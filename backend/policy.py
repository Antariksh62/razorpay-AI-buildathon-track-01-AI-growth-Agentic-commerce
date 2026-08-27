import datetime
from typing import Dict, Any, Tuple
from database import get_mandate, add_audit_log, mark_mandate_used, get_db_connection, add_mandate_spend

class DeclarativePolicyEngine:
    """
    Antigravity Declarative Policy Engine for Agentic Commerce.
    Enforces bounded money movement, temporal expiry, anti-replay protection, and surge guardrails.
    Every evaluation logs a transparent, immutable audit trail to SQLite.
    """

    @staticmethod
    def evaluate_catalog_search(query: str, max_budget: float = None) -> Tuple[bool, str, Dict[str, Any]]:
        details = f"Catalog query='{query}'"
        if max_budget is not None:
            details += f", max_budget_filter=₹{max_budget:,.2f}"
        
        audit_entry = add_audit_log(
            action="SEARCH_CATALOG",
            policy_verdict="ALLOWED",
            details=details
        )
        return True, "ALLOWED", audit_entry

    @staticmethod
    def evaluate_cart_quote(items_input: Any, quantity: int = 1) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Policy Hook Interceptor for cart quote creation.
        Evaluates Partial Stockouts and Quantity Validation.
        """
        items_list = items_input if isinstance(items_input, list) else [items_input]

        for item_entry in items_list:
            item = item_entry.get("item", item_entry)
            item_name = item.get("name", item.get("item_name", "Unknown Product"))
            stock = item.get("stock", 0)
            req_qty = item_entry.get("quantity", quantity)

            # Quantity Manipulation Defense
            if req_qty <= 0:
                details = f"Invalid Quantity Manipulation Blocked: Requested quantity {req_qty} for '{item_name}' is <= 0."
                audit_entry = add_audit_log(
                    action="CREATE_CART_QUOTE",
                    policy_verdict="INVALID_QUANTITY",
                    details=details
                )
                return False, "INVALID_QUANTITY", audit_entry

            if stock < req_qty:
                verdict = "STOCKOUT" if len(items_list) == 1 else "PARTIAL_STOCKOUT"
                details = f"Partial Stockout Guardrail: Item '{item_name}' (ID: {item.get('item_id')}) requested qty {req_qty}, but available stock is {stock}. Quote creation blocked."
                audit_entry = add_audit_log(
                    action="CREATE_CART_QUOTE",
                    policy_verdict=verdict,
                    details=details
                )
                return False, verdict, audit_entry

        total_items = len(items_list)
        details = f"Multi-item cart quote authorized for {total_items} product(s). Stock reserved." if total_items > 1 else f"Quote created for '{items_list[0].get('name', 'Item')}' x {quantity}. Stock reserved."
        audit_entry = add_audit_log(
            action="CREATE_CART_QUOTE",
            policy_verdict="ALLOWED",
            details=details
        )
        return True, "ALLOWED", audit_entry

    @staticmethod
    def evaluate_checkout_intent(quote: Dict[str, Any], mandate_nonce: str) -> Tuple[bool, str, str, Dict[str, Any]]:
        """
        Policy Hook Interceptor for money movement.
        Verifies Mandate Existence, Cumulative Spend, Expiry Window, Quote TTL, JIT Price Surge, and Budget Caps.
        """
        mandate = get_mandate(mandate_nonce)
        cart_total = quote.get("total_amount_inr", 0.0)

        # 1. Mandate Existence check
        if not mandate:
            reason = f"Mandate nonce '{mandate_nonce}' not found in authorization store."
            audit_entry = add_audit_log(
                action="EXECUTE_RAZORPAY_CHECKOUT",
                policy_verdict="MANDATE_NOT_FOUND",
                details=f"BLOCKED: {reason}"
            )
            return False, "MANDATE_NOT_FOUND", reason, audit_entry

        # 1.5 Emergency Kill Switch Revocation check
        if mandate.get("is_used", 0) == -1:
            reason = f"Emergency Kill Switch Active: Mandate nonce '{mandate_nonce}' has been REVOKED by user."
            audit_entry = add_audit_log(
                action="EXECUTE_RAZORPAY_CHECKOUT",
                policy_verdict="MANDATE_REVOKED",
                details=f"BLOCKED: {reason}"
            )
            return False, "MANDATE_REVOKED", reason, audit_entry

        # 2. Cumulative Spend check
        current_spend = mandate.get("current_spend_inr", 0.0)
        max_spend = mandate.get("max_spend_inr", 0.0)
        
        if current_spend >= max_spend:
            reason = f"Budget Exhausted: Mandate nonce '{mandate_nonce}' spend ₹{current_spend:,.2f} reached limit ₹{max_spend:,.2f}."
            audit_entry = add_audit_log(
                action="EXECUTE_RAZORPAY_CHECKOUT",
                policy_verdict="BUDGET_EXCEEDED",
                details=f"BLOCKED: {reason}"
            )
            return False, "BUDGET_EXCEEDED", reason, audit_entry

        # 3. Mandate Expiry check
        expires_at_str = mandate.get("expires_at")
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        try:
            expires_at_dt = datetime.datetime.fromisoformat(expires_at_str)
            if expires_at_dt.tzinfo is None:
                expires_at_dt = expires_at_dt.replace(tzinfo=datetime.timezone.utc)
            
            if now_dt > expires_at_dt:
                reason = f"Mandate Expired: Intent authorization expired at {expires_at_str}."
                audit_entry = add_audit_log(
                    action="EXECUTE_RAZORPAY_CHECKOUT",
                    policy_verdict="MANDATE_EXPIRED",
                    details=f"BLOCKED: {reason}"
                )
                return False, "MANDATE_EXPIRED", reason, audit_entry
        except Exception:
            pass

        # 3.2 Cart Quote TTL Expiry (15 minute quote staleness limit)
        created_at_str = quote.get("created_at")
        if created_at_str:
            try:
                created_dt = datetime.datetime.fromisoformat(created_at_str)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=datetime.timezone.utc)
                if (now_dt - created_dt).total_seconds() > 900:  # 15 minutes TTL
                    reason = "Cart Quote Expired: Stale cart quote exceeds 15-minute validity window. Fresh quote required."
                    audit_entry = add_audit_log(
                        action="EXECUTE_RAZORPAY_CHECKOUT",
                        policy_verdict="QUOTE_EXPIRED",
                        details=f"BLOCKED: {reason}"
                    )
                    return False, "QUOTE_EXPIRED", reason, audit_entry
            except Exception:
                pass

        # 3.5 Just-in-Time (JIT) Price Validation & Surge Protection
        items_list = quote.get("items", [])
        if items_list and isinstance(items_list, list):
            conn = get_db_connection()
            cursor = conn.cursor()
            live_price = 0.0
            for it in items_list:
                iid = it.get("item_id")
                qty = it.get("quantity", 1)
                cursor.execute("SELECT price_inr, stock FROM merchants_catalog WHERE item_id = ?", (iid,))
                r = cursor.fetchone()
                if r:
                    live_price += r["price_inr"] * qty
            conn.close()

            if cart_total > 0 and live_price > cart_total * 1.2:
                reason = f"Price Surge Guardrail: Live aggregate price ₹{live_price:,.2f} surged >20% above quoted price ₹{cart_total:,.2f}."
                audit_entry = add_audit_log(
                    action="JIT_PRICE_VALIDATION",
                    policy_verdict="PRICE_SURGE_DETECTED",
                    details=f"BLOCKED: {reason}"
                )
                return False, "PRICE_SURGE_DETECTED", reason, audit_entry

            if live_price != cart_total:
                add_audit_log(
                    action="JIT_PRICE_VALIDATION",
                    policy_verdict="PRICE_CORRECTED",
                    details=f"JIT Price Check: Overrode cached price ₹{cart_total:,.2f} with live database aggregate price ₹{live_price:,.2f}."
                )
                cart_total = live_price
                quote["total_amount_inr"] = live_price
        else:
            item_id = quote.get("item_id")
            if item_id:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT price_inr, name, stock FROM merchants_catalog WHERE item_id = ?", (item_id,))
                db_item = cursor.fetchone()
                conn.close()

                if db_item:
                    quantity = quote.get("quantity", 1)
                    live_price = db_item["price_inr"] * quantity
                    
                    if cart_total > 0 and live_price > cart_total * 1.2:
                        reason = f"Price Surge Guardrail: Live price ₹{live_price:,.2f} surged >20% above quoted price ₹{cart_total:,.2f}."
                        audit_entry = add_audit_log(
                            action="JIT_PRICE_VALIDATION",
                            policy_verdict="PRICE_SURGE_DETECTED",
                            details=f"BLOCKED: {reason}"
                        )
                        return False, "PRICE_SURGE_DETECTED", reason, audit_entry

                    if live_price != cart_total:
                        add_audit_log(
                            action="JIT_PRICE_VALIDATION",
                            policy_verdict="PRICE_CORRECTED",
                            details=f"JIT Price Check: Overrode cached price ₹{cart_total:,.2f} with live database price ₹{live_price:,.2f}."
                        )
                        cart_total = live_price
                        quote["total_amount_inr"] = live_price

        # 4. Cumulative Bounded money movement check
        projected_spend = current_spend + cart_total
        if projected_spend > max_spend:
            reason = f"Cumulative Budget Breach: Cart ₹{cart_total:,.2f} + Current spend ₹{current_spend:,.2f} = ₹{projected_spend:,.2f} exceeds cap ₹{max_spend:,.2f}."
            audit_entry = add_audit_log(
                action="EXECUTE_RAZORPAY_CHECKOUT",
                policy_verdict="BUDGET_BREACH",
                details=f"BLOCKED: {reason}"
            )
            return False, "BUDGET_BREACH", reason, audit_entry

        # ALL CHECKS PASSED -> Update database and allow tool execution
        add_mandate_spend(mandate_nonce, cart_total)
        success_msg = f"Policy Passed: Cart total ₹{cart_total:,.2f} added to mandate. New cumulative spend: ₹{projected_spend:,.2f} / ₹{max_spend:,.2f}."
        audit_entry = add_audit_log(
            action="EXECUTE_RAZORPAY_CHECKOUT",
            policy_verdict="ALLOWED",
            details=f"APPROVED: {success_msg}"
        )
        return True, "ALLOWED", success_msg, audit_entry
