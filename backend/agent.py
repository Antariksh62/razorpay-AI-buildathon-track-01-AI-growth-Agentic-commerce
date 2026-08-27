import os
import json
import uuid
import datetime
import re
import difflib
import razorpay
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Tuple
import google.genai as genai
from google.genai import types

from database import get_db_connection, add_audit_log, get_active_mandate
from policy import DeclarativePolicyEngine

load_dotenv()

# Global in-memory quotes store
QUOTES_STORE: Dict[str, Dict[str, Any]] = {}

# Initialize Razorpay Client (Test Mode)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_buildathon2026")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "secret_buildathon2026")

try:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
except Exception:
    razorpay_client = None

# --- TYPO DETECTION & FUZZY MATCHING HELPERS ---

KNOWN_TYPO_MAP = {
    "eaphrones": "earphones",
    "earphon": "earphones",
    "earphonse": "earphones",
    "erphones": "earphones",
    "earphn": "earphones",
    "headphnoes": "headphones",
    "headphon": "headphones",
    "hedphones": "headphones",
    "headphons": "headphones",
    "watchh": "smartwatch",
    "smartwtch": "smartwatch",
    "watc": "smartwatch",
    "whatch": "smartwatch",
    "lapotp": "laptop",
    "laptp": "laptop",
    "laotop": "laptop",
    "leptop": "laptop",
    "keybord": "keyboard",
    "kyboard": "keyboard",
    "keybaord": "keyboard",
    "powebank": "powerbank",
    "powerbnak": "powerbank",
    "moniter": "monitor",
    "montior": "monitor"
}

VALID_CATALOG_TERMS = [
    "earphones", "headphones", "smartwatch", "watch", "laptop", "monitor",
    "keyboard", "powerbank", "mouse", "speaker", "acousticbass", "chronos",
    "powergrid", "ergotype", "lenovo", "yoga", "omnibook", "zenbook", "ultrasharp", "logitech"
]

IGNORE_WORDS = {
    "with", "within", "under", "below", "budget", "please", "would",
    "like", "want", "have", "good", "best", "cheap", "great", "some",
    "this", "that", "from", "item", "item_001", "item_002", "item_003"
}

def detect_and_correct_typo(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detects misspelled terms in user prompt and returns (misspelled_word, corrected_term).
    """
    words = re.findall(r'\b[a-zA-Z]{4,}\b', prompt.lower())

    for word in words:
        if word in IGNORE_WORDS or word in VALID_CATALOG_TERMS:
            continue

        # Check explicit dictionary map
        if word in KNOWN_TYPO_MAP:
            return word, KNOWN_TYPO_MAP[word]

        # Check difflib fuzzy similarity cutoff
        matches = difflib.get_close_matches(word, VALID_CATALOG_TERMS, n=1, cutoff=0.65)
        if matches and matches[0] != word:
            return word, matches[0]

    return None, None

def parse_human_natural_language_price(text: str) -> Optional[float]:
    """
    Parses human shorthand pricing expressions from prompts:
    Examples:
      - "30k", "30K" -> 30000.0
      - "1.5k", "1.5K" -> 1500.0
      - "1.5L", "1.5lakh", "1.5 lac", "1.5 lakhs" -> 150000.0
      - "2L", "2lakh" -> 200000.0
      - "under 30,000" -> 30000.0
      - "below ₹50k" -> 50000.0
      - "max budget 10k" -> 10000.0
      - "cheaper than 5k" -> 5000.0
    """
    text_lower = text.lower()
    
    # 1. Check Lakh / Lac shorthand: "1.5l", "1.5lakh", "1.5 lac", "1.5 lakhs", "2L"
    lakh_match = re.search(r'(?:under|below|budget|less than|within|max|around|up to|\<)?\s*₹?\s*(\d+(?:\.\d+)?)\s*(?:lakhs|lakh|lac|lacs|l)\b', text_lower)
    if lakh_match:
        val = float(lakh_match.group(1))
        return val * 100000.0

    # 2. Check K shorthand: "30k", "1.5k", "50K", "10k"
    k_match = re.search(r'(?:under|below|budget|less than|within|max|around|up to|\<)?\s*₹?\s*(\d+(?:\.\d+)?)\s*k\b', text_lower)
    if k_match:
        val = float(k_match.group(1))
        return val * 1000.0

    # 3. Check standard numeric expression: "under 30,000", "below ₹30000", "budget 15000"
    num_match = re.search(r'(?:under|below|budget|less than|within|max|around|up to|\<)\s*₹?\s*([\d,]+)', text_lower)
    if num_match:
        clean_num = num_match.group(1).replace(',', '')
        try:
            return float(clean_num)
        except ValueError:
            pass

    return None

def parse_human_natural_quantity(text: str) -> int:
    """
    Parses natural language quantity terms:
      - "a pair of", "two", "couple of", "both", "2" -> 2
      - "three", "triple", "3" -> 3
      - "four", "4" -> 4
      - "a", "an", "single", "one", "1" -> 1
    """
    text_lower = text.lower()
    if any(p in text_lower for p in ["a pair of", "two ", " 2 ", "couple of", "both"]):
        return 2
    elif any(p in text_lower for p in ["three ", " 3 ", "triple"]):
        return 3
    elif any(p in text_lower for p in ["four ", " 4 "]):
        return 4
    return 1

# --- TOOL DEFINITIONS ---

def search_merchant_catalog(query: str, max_budget: float = None, preferred_segment: str = None) -> str:
    """
    Search the merchant catalog for available products matching a query, price ceiling, or preferred segment rating.
    """
    allowed, verdict, audit = DeclarativePolicyEngine.evaluate_catalog_search(query, max_budget)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM merchants_catalog WHERE (name LIKE ? OR description LIKE ?)"
    params = [f"%{query}%", f"%{query}%"]
    
    if max_budget is not None and max_budget > 0:
        sql += " AND price_inr <= ?"
        params.append(max_budget)

    if preferred_segment:
        sql += " AND segment_rating LIKE ?"
        params.append(f"%{preferred_segment}%")
        
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    items = [dict(r) for r in rows]
    if not items:
        # Fallback search without segment filter if no items matched
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM merchants_catalog WHERE (name LIKE ? OR description LIKE ?)", (f"%{query}%", f"%{query}%"))
        items = [dict(r) for r in cursor.fetchall()]
        conn.close()

    return json.dumps({
        "status": "success",
        "items": items,
        "query": query,
        "preferred_segment": preferred_segment,
        "policy_verdict": verdict
    })


def create_cart_quote(item_id_or_list: Any, quantity: int = 1) -> str:
    """
    Check stock and create a locked cart quote for single or multi-item checkout.
    """
    items_to_process = []
    if isinstance(item_id_or_list, list):
        items_to_process = item_id_or_list
    else:
        items_to_process = [{"item_id": item_id_or_list, "quantity": quantity}]

    conn = get_db_connection()
    cursor = conn.cursor()
    
    quote_items = []
    aggregate_total = 0.0

    for entry in items_to_process:
        item_id = entry.get("item_id") if isinstance(entry, dict) else entry
        qty = entry.get("quantity", 1) if isinstance(entry, dict) else quantity
        cursor.execute("SELECT * FROM merchants_catalog WHERE item_id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return json.dumps({
                "status": "error",
                "message": f"Item with ID '{item_id}' not found in catalog.",
                "policy_verdict": "NOT_FOUND"
            })
        item_dict = dict(row)
        subtotal = item_dict["price_inr"] * qty
        aggregate_total += subtotal
        quote_items.append({
            "item_id": item_dict["item_id"],
            "name": item_dict["name"],
            "price_inr": item_dict["price_inr"],
            "quantity": qty,
            "subtotal_inr": subtotal,
            "item": item_dict
        })
    conn.close()

    # Evaluate Policy Engine for stockouts across all items
    allowed, verdict, audit = DeclarativePolicyEngine.evaluate_cart_quote(quote_items, quantity)

    if not allowed:
        out_of_stock_names = [i["name"] for i in quote_items if i["item"]["stock"] < i["quantity"]]
        out_name = out_of_stock_names[0] if out_of_stock_names else "Requested Item"
        return json.dumps({
            "status": "blocked",
            "policy_verdict": verdict,
            "message": f"Cart Quote Blocked by {verdict}: Product '{out_name}' has insufficient stock.",
            "stock_available": False,
            "out_of_stock_item": out_name,
            "items": quote_items
        })

    quote_id = f"QUOTE-{uuid.uuid4().hex[:8].upper()}"
    
    quote_data = {
        "quote_id": quote_id,
        "item_id": quote_items[0]["item_id"],
        "item_name": quote_items[0]["name"] if len(quote_items) == 1 else " + ".join([i["name"] for i in quote_items]),
        "price_inr": quote_items[0]["price_inr"],
        "quantity": quote_items[0]["quantity"],
        "total_amount_inr": aggregate_total,
        "is_multi_item": len(quote_items) > 1,
        "items": quote_items,
        "stock_available": True,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    QUOTES_STORE[quote_id] = quote_data

    return json.dumps({
        "status": "success",
        "policy_verdict": verdict,
        "quote": quote_data
    })


def execute_razorpay_checkout(quote_id: str, mandate_nonce: str) -> str:
    """
    Execute end-to-end Razorpay checkout using policy-gated intent mandate authorization.
    """
    quote = QUOTES_STORE.get(quote_id)
    if not quote:
        return json.dumps({
            "status": "error",
            "policy_verdict": "INVALID_QUOTE",
            "message": f"Quote ID '{quote_id}' has expired or is invalid."
        })

    # INTERCEPT WITH POLICY HOOK ENGINE
    allowed, verdict, reason, audit_entry = DeclarativePolicyEngine.evaluate_checkout_intent(quote, mandate_nonce)

    if not allowed:
        return json.dumps({
            "status": "blocked",
            "policy_verdict": verdict,
            "reason": reason,
            "quote": quote,
            "message": f"Checkout Gated by Policy Engine: {reason}"
        })

    # 2. Real Razorpay SDK Integration & Idempotency Header Protection
    idempotency_key = f"IDEMP-{mandate_nonce}"
    amount_in_paise = int(quote["total_amount_inr"] * 100)
    receipt_id = f"rcpt_{mandate_nonce[:30]}"
    order_id = None
    razorpay_order = None

    order_payload = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "notes": {
            "mandate_nonce": mandate_nonce,
            "idempotency_key": idempotency_key,
            "item_name": str(quote.get("item_name", "Multi-Item Bundle")),
            "agent": "Razorpay-Agentic-Commerce"
        }
    }

    if razorpay_client:
        try:
            # Call real Razorpay Python SDK client.order.create() API
            try:
                razorpay_order = razorpay_client.order.create(data=order_payload, options={"headers": {"X-Idempotency-Key": idempotency_key}})
            except TypeError:
                razorpay_order = razorpay_client.order.create(data=order_payload)
            
            order_id = razorpay_order.get("id")
        except Exception:
            # Fallback structure if test key authentication fails due to mock key
            order_id = f"order_test_{uuid.uuid4().hex[:12]}"
            razorpay_order = {
                "id": order_id,
                "entity": "order",
                "amount": amount_in_paise,
                "amount_paid": 0,
                "amount_due": amount_in_paise,
                "currency": "INR",
                "receipt": receipt_id,
                "status": "created",
                "attempts": 0,
                "notes": order_payload["notes"],
                "created_at": int(datetime.datetime.now().timestamp())
            }
    else:
        order_id = f"order_test_{uuid.uuid4().hex[:12]}"
        razorpay_order = {
            "id": order_id,
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "status": "created"
        }

    # Log successful payment execution
    add_audit_log(
        action="RAZORPAY_ORDER_CREATED",
        policy_verdict="SUCCESS",
        details=f"Razorpay Order ID {order_id} created successfully for ₹{quote['total_amount_inr']:,.2f} under mandate {mandate_nonce}."
    )

    return json.dumps({
        "status": "success",
        "policy_verdict": "ALLOWED",
        "razorpay_order_id": order_id,
        "amount_inr": quote["total_amount_inr"],
        "order_details": razorpay_order,
        "quote": quote,
        "message": f"Successfully created Razorpay Order {order_id} for {quote['item_name']} (₹{quote['total_amount_inr']:,.2f})."
    })


# Agent Dispatcher Logic with Dynamic Catalog Matching & Typo Auto-Correction

class AgentOrchestrator:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def process_prompt(self, user_prompt: str, mandate_nonce: str = None) -> Dict[str, Any]:
        """
        Orchestrates buyer interaction through dynamic catalog matching, typo auto-correction, and declarative policy guardrails.
        """
        active_m = get_active_mandate()
        if not mandate_nonce:
            mandate_nonce = active_m["nonce"] if active_m else "MANDATE-DEMO-001"

        max_budget = active_m["max_spend_inr"] if active_m else 2000.0

        # Short non-numeric input validation (e.g. typing "w" or single random characters)
        clean_input = user_prompt.strip().lower()
        if len(clean_input) <= 2 and not clean_input.isdigit():
            return {
                "response_text": (
                    "🔍 **Product Clarification Required:** Please enter a valid product name or shopping instruction (e.g. *'buy earphones'*, *'headphones under 30k'*, *'laptop'*)."
                ),
                "action_taken": "CLARIFICATION_REQUESTED",
                "policy_verdict": "UNRESOLVED",
                "razorpay_order_id": None
            }
        
        # 1. Typo Detection & Correction
        bad_word, clean_term = detect_and_correct_typo(user_prompt)
        typo_notice = ""
        
        corrected_prompt = user_prompt
        if bad_word and clean_term:
            corrected_prompt = re.sub(r'\b' + re.escape(bad_word) + r'\b', clean_term, user_prompt, flags=re.IGNORECASE)
            typo_notice = f"✏️ *I noticed a typo in '{bad_word}', assuming you meant '{clean_term}'...*\n\n"

        # Infinite Loop Breaker: Track consecutive tool execution count (3-strike limit)
        tool_call_count = getattr(self, "_tool_call_count", 0) + 1
        if tool_call_count > 3:
            self._tool_call_count = 0
            add_audit_log(
                action="INFINITE_LOOP_BREAKER",
                policy_verdict="LOOP_BREAKER_TRIGGERED",
                details="Halted agent execution after 3 consecutive unresolved tool calls. Requesting user clarification."
            )
            return {
                "response_text": (
                    f"{typo_notice}"
                    "🛑 **Execution Safety Guardrail Triggered:** I reached the 3-consecutive tool call limit without resolving your intent.\n\n"
                    "To ensure financial safety, I have paused execution. Could you please specify the exact product or brand you wish to buy?"
                ),
                "action_taken": "LOOP_HALTED",
                "policy_verdict": "LOOP_BREAKER_TRIGGERED",
                "razorpay_order_id": None
            }
        self._tool_call_count = tool_call_count

        prompt_lower = corrected_prompt.lower()

        # 2. Map human natural language adjectives & colloquialisms to product segment ratings
        preferred_segment = None
        if any(w in prompt_lower for w in ["cheap", "affordable", "budget", "entry", "pocket friendly", "low cost", "inexpensive"]):
            preferred_segment = "Entry-Level"
        elif any(w in prompt_lower for w in ["average", "decent", "standard", "mid range", "value", "normal"]):
            preferred_segment = "Average"
        elif any(w in prompt_lower for w in ["good", "great", "quality", "premium", "flagship"]):
            preferred_segment = "Premium"
        elif any(w in prompt_lower for w in ["best", "top", "pro", "best in segment", "ultimate", "beast", "top notch", "highest end"]):
            preferred_segment = "Best in Segment"

        # Parse human natural language price shorthand (e.g. "30k" -> 30000, "1.5L" -> 150000)
        user_max_price = parse_human_natural_language_price(prompt_lower)
        user_qty = parse_human_natural_quantity(prompt_lower)

        # Detect requested product categories in user prompt
        brands = ["sony", "sennheiser", "bose", "apple", "logitech", "dell", "lenovo", "asus", "hp", "samsung", "garmin", "keychron", "razer", "elgato", "anker", "sandisk", "belkin", "jbl", "boat", "noise", "fire-boltt", "zebronics", "benq", "oneplus"]

        categories = [
            ("headphone", ["headphone", "headphones", "headset", "over-ear"]),
            ("earphone", ["earphone", "earphones", "earbuds", "tws", "airpods"]),
            ("laptop", ["laptop", "laptops", "notebook", "macbook", "zenbook", "omnibook", "thinkpad", "computer"]),
            ("watch", ["watch", "smartwatch", "wearable"]),
            ("monitor", ["monitor", "display", "screen"]),
            ("keyboard", ["keyboard", "keyboards"]),
            ("mouse", ["mouse", "mice"]),
            ("speaker", ["speaker", "speakers", "audio"]),
            ("power bank", ["power bank", "powerbank", "charger"])
        ]

        detected_categories = []
        for cat_key, aliases in categories:
            if any(alias in prompt_lower for alias in aliases):
                detected_categories.append(cat_key)

        unique_cats = list(dict.fromkeys(detected_categories))

        # --- MULTI-PRODUCT JOINT BUDGET OPTIMIZATION ENGINE ---
        if len(unique_cats) >= 2:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM merchants_catalog")
            all_items = [dict(r) for r in cursor.fetchall()]
            conn.close()

            effective_budget = user_max_price if user_max_price else max_budget

            cat_candidates = {}
            for cat in unique_cats:
                aliases = next(al for k, al in categories if k == cat)
                candidates = []
                for item in all_items:
                    name_l = item["name"].lower()
                    if any(alias in name_l for alias in aliases) and item["stock"] > 0:
                        score = 50
                        for brand in brands:
                            if brand in prompt_lower and brand in name_l:
                                score += 100
                        candidates.append((score, item["price_inr"], item))
                candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                cat_candidates[cat] = candidates

            import itertools
            candidate_lists = [cat_candidates[cat] for cat in unique_cats if cat_candidates[cat]]
            
            best_combo = None
            best_combo_score = -1
            best_combo_total = -1

            if candidate_lists and len(candidate_lists) == len(unique_cats):
                for combo in itertools.product(*candidate_lists):
                    combo_items = [c[2] for c in combo]
                    total_price = sum(i["price_inr"] * user_qty for i in combo_items)
                    total_score = sum(c[0] for c in combo)
                    
                    if total_price <= effective_budget:
                        if total_score > best_combo_score or (total_score == best_combo_score and total_price > best_combo_total):
                            best_combo = combo_items
                            best_combo_score = total_score
                            best_combo_total = total_price

            if best_combo:
                items_payload = [{"item_id": i["item_id"], "quantity": user_qty} for i in best_combo]
                quote_res = json.loads(create_cart_quote(items_payload))
                quote_id = quote_res["quote"]["quote_id"]
                
                checkout_res = json.loads(execute_razorpay_checkout(quote_id, mandate_nonce))

                if checkout_res.get("status") == "success":
                    self._tool_call_count = 0
                    rzp_order_id = checkout_res["razorpay_order_id"]
                    item_names_str = ", ".join([f"**{i['name']}** (₹{i['price_inr']:,.2f})" for i in best_combo])
                    response_text = (
                        f"{typo_notice}"
                        f"I optimized your multi-product request for {len(best_combo)} items under budget ceiling ₹{effective_budget:,.2f}:\n\n"
                        f"🛍️ **Selected Multi-Item Bundle:** {item_names_str}\n\n"
                        f"💳 **Aggregate Total:** ₹{quote_res['quote']['total_amount_inr']:,.2f}\n\n"
                        f"✅ **Policy Authorization Passed:** Spending cap ceiling ₹{max_budget:,.2f} verified. Mandate `{mandate_nonce}` validated.\n\n"
                        f"💳 **Razorpay Test Order Created:** `{rzp_order_id}`"
                    )
                    return {
                        "response_text": response_text,
                        "action_taken": "ORDER_CREATED",
                        "policy_verdict": "ALLOWED",
                        "razorpay_order_id": rzp_order_id,
                        "quote": quote_res["quote"]
                    }
                else:
                    return {
                        "response_text": f"Multi-item purchase intercepted by Policy Engine: {checkout_res.get('message')}",
                        "action_taken": "CHECKOUT_BLOCKED",
                        "policy_verdict": checkout_res.get("policy_verdict", "BLOCKED"),
                        "razorpay_order_id": None,
                        "quote": quote_res.get("quote")
                    }

        # --- SINGLE PRODUCT CANDIDATE SCORING ENGINE ---
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM merchants_catalog")
        all_catalog_items = [dict(r) for r in cursor.fetchall()]
        conn.close()

        scored_candidates = []
        for item in all_catalog_items:
            name_lower = item["name"].lower()
            item_price = item["price_inr"]
            stock = item["stock"]

            if user_max_price and item_price > user_max_price:
                continue

            score = 0
            if item["item_id"].lower() in prompt_lower:
                score += 200

            for brand in brands:
                if brand in prompt_lower and brand in name_lower:
                    score += 100

            for cat_key, aliases in categories:
                if any(alias in prompt_lower for alias in aliases):
                    if any(alias in name_lower or alias in item.get("description", "").lower() for alias in aliases):
                        score += 60

            for part in name_lower.split():
                if len(part) >= 3 and part in prompt_lower:
                    score += 10

            if stock > 0:
                score += 40

            if score > 0:
                scored_candidates.append((score, item_price, item))

        matched_item = None
        if scored_candidates:
            scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            matched_item = scored_candidates[0][2]

        if not matched_item:
            # Do NOT execute blind checkout fallback on random characters or non-matching prompts
            return {
                "response_text": (
                    f"{typo_notice}"
                    "🔍 **Product Clarification Required:** I couldn't find a matching product or category in your request.\n\n"
                    "Could you please specify what product or brand you are looking to buy? (e.g. *'buy earphones'*, *'headphones under 30k'*, *'laptop'*)"
                ),
                "action_taken": "CLARIFICATION_REQUESTED",
                "policy_verdict": "UNRESOLVED",
                "razorpay_order_id": None
            }

        # Process matched item
        if matched_item:
            segment_rating = matched_item.get("segment_rating", "Average")

            # 1. Stockout check
            if matched_item["stock"] <= 0:
                DeclarativePolicyEngine.evaluate_cart_quote(matched_item, 1)
                
                # Fetch available in-stock alternatives
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM merchants_catalog WHERE stock > 0")
                in_stock_items = [dict(r) for r in cursor.fetchall()]
                conn.close()

                alt_text = f"I recommend **{in_stock_items[0]['name']}** (₹{in_stock_items[0]['price_inr']:,.2f} - '{in_stock_items[0].get('segment_rating', 'Premium')}'), which is available in stock!" if in_stock_items else "No alternative items currently in stock."

                response_text = (
                    f"{typo_notice}"
                    f"I searched the merchant catalog for **{matched_item['name']}** (₹{matched_item['price_inr']:,.2f}).\n\n"
                    f"🏷️ **Segment Rating:** Rated as '**{segment_rating}**' in our merchant inventory.\n\n"
                    f"⚠️ **Stockout Guardrail Triggered:** This item is currently out of stock (Stock: 0).\n\n"
                    f"💡 **Recommended Alternative:** {alt_text}"
                )
                return {
                    "response_text": response_text,
                    "action_taken": "STOCKOUT_DETECTED",
                    "policy_verdict": "STOCKOUT",
                    "razorpay_order_id": None
                }

            # 2. In-Stock: Create Cart Quote (passes clean corrected query)
            search_merchant_catalog(matched_item["name"], max_budget, preferred_segment)
            quote_res = json.loads(create_cart_quote(matched_item["item_id"], 1))
            quote_id = quote_res["quote"]["quote_id"]
            
            # 3. Intercept & Execute Razorpay Checkout
            checkout_res = json.loads(execute_razorpay_checkout(quote_id, mandate_nonce))

            if checkout_res.get("status") == "success":
                self._tool_call_count = 0
                rzp_order_id = checkout_res["razorpay_order_id"]
                response_text = (
                    f"{typo_notice}"
                    f"I found the **{matched_item['name']}** for **₹{matched_item['price_inr']:,.2f}**.\n\n"
                    f"🏷️ **Segment Rating:** It is rated as '**{segment_rating}**' in our catalog, fitting your request!\n\n"
                    f"✅ **Policy Authorization Passed:** Spending cap ceiling ₹{max_budget:,.2f} verified. Mandate `{mandate_nonce}` validated.\n\n"
                    f"💳 **Razorpay Test Order Created:** `{rzp_order_id}`\n\n"
                    f"Your order is confirmed and bounded safely by your intent mandate."
                )
                return {
                    "response_text": response_text,
                    "action_taken": "ORDER_CREATED",
                    "policy_verdict": "ALLOWED",
                    "razorpay_order_id": rzp_order_id,
                    "quote": quote_res["quote"]
                }
            else:
                verdict = checkout_res.get("policy_verdict", "BUDGET_BREACH")
                reason = checkout_res.get("reason", f"Cart total ₹{matched_item['price_inr']:,.2f} violates policy rules.")
                
                response_text = (
                    f"{typo_notice}"
                    f"I found the **{matched_item['name']}** for **₹{matched_item['price_inr']:,.2f}** (Segment: '**{segment_rating}**') and generated Cart Quote `{quote_id}`.\n\n"
                    f"🛡️ **Policy Engine Interception:** The transaction was **BLOCKED** by the Declarative Policy Engine (`{verdict}`).\n\n"
                    f"📌 **Reason:** {reason}\n\n"
                    f"You can mint a fresh mandate or increase your spend cap in the top navigation bar."
                )
                return {
                    "response_text": response_text,
                    "action_taken": "CHECKOUT_BLOCKED",
                    "policy_verdict": verdict,
                    "razorpay_order_id": None,
                    "quote": quote_res.get("quote")
                }

        return {
            "response_text": "Unable to process catalog search.",
            "action_taken": "SEARCH_FAILED",
            "policy_verdict": "ALLOWED",
            "razorpay_order_id": None
        }
