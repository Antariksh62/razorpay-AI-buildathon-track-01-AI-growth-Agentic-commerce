import sqlite3
import json
import os
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "app.db"

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency and ACID compliance
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(force_recreate: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()

    if force_recreate:
        cursor.execute("DROP TABLE IF EXISTS merchants_catalog")

    # 1. Merchants Catalog with segment_rating
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchants_catalog (
            item_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price_inr REAL NOT NULL,
            stock INTEGER NOT NULL,
            delivery_days INTEGER NOT NULL,
            description TEXT,
            segment_rating TEXT DEFAULT 'Average'
        )
    """)

    # Migration check: ensure segment_rating column exists if table existed previously
    cursor.execute("PRAGMA table_info(merchants_catalog)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "segment_rating" not in columns:
        cursor.execute("ALTER TABLE merchants_catalog ADD COLUMN segment_rating TEXT DEFAULT 'Average'")

    # 2. Intent Mandates with Cumulative Spend Support
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intent_mandates (
            nonce TEXT PRIMARY KEY,
            max_spend_inr REAL NOT NULL,
            current_spend_inr REAL DEFAULT 0.0,
            expires_at TEXT NOT NULL,
            is_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # Migration check: ensure current_spend_inr column exists
    cursor.execute("PRAGMA table_info(intent_mandates)")
    mandate_cols = [row["name"] for row in cursor.fetchall()]
    if "current_spend_inr" not in mandate_cols:
        cursor.execute("ALTER TABLE intent_mandates ADD COLUMN current_spend_inr REAL DEFAULT 0.0")

    # 3. Audit Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            policy_verdict TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)
    conn.commit()

    # Seed catalog data if empty or forced
    cursor.execute("SELECT COUNT(*) as count FROM merchants_catalog")
    row = cursor.fetchone()
    if row["count"] == 0 or force_recreate:
        mock_file = Path(__file__).parent / "mock_data.json"
        if mock_file.exists():
            with open(mock_file, "r", encoding="utf-8") as f:
                items = json.load(f)
                for item in items:
                    cursor.execute("""
                        INSERT OR REPLACE INTO merchants_catalog (item_id, name, price_inr, stock, delivery_days, description, segment_rating)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item["item_id"],
                        item["name"],
                        item["price_inr"],
                        item["stock"],
                        item["delivery_days"],
                        item.get("description", ""),
                        item.get("segment_rating", "Average")
                    ))
            conn.commit()
            add_audit_log(
                action="SYSTEM_INIT",
                policy_verdict="ALLOWED",
                details="Seeded merchant catalog with Product Segment Ratings into SQLite database (WAL mode)."
            )
    
    # Create default mandate if none exists
    cursor.execute("SELECT COUNT(*) as count FROM intent_mandates")
    row = cursor.fetchone()
    if row["count"] == 0:
        default_nonce = "MANDATE-DEMO-001"
        expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)).isoformat()
        cursor.execute("""
            INSERT INTO intent_mandates (nonce, max_spend_inr, current_spend_inr, expires_at, is_used, created_at)
            VALUES (?, ?, 0.0, ?, 0, ?)
        """, (default_nonce, 2000.0, expires_at, datetime.datetime.now(datetime.timezone.utc).isoformat()))
        conn.commit()
        add_audit_log(
            action="MANDATE_CREATED",
            policy_verdict="ALLOWED",
            details=f"Created default intent mandate {default_nonce} with max budget ₹2,000.00."
        )

    conn.close()

def add_audit_log(action: str, policy_verdict: str, details: str) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO audit_logs (timestamp, action, policy_verdict, details)
        VALUES (?, ?, ?, ?)
    """, (now_str, action, policy_verdict, details))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": log_id,
        "timestamp": now_str,
        "action": action,
        "policy_verdict": policy_verdict,
        "details": details
    }

def get_recent_audit_logs(limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_mandate(nonce: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM intent_mandates WHERE nonce = ?", (nonce,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_active_mandate():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM intent_mandates ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def set_mandate(max_spend_inr: float, duration_minutes: int = 60) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = (now + datetime.timedelta(minutes=duration_minutes)).isoformat()
    nonce = f"MANDATE-{int(now.timestamp())}"
    
    cursor.execute("""
        INSERT INTO intent_mandates (nonce, max_spend_inr, current_spend_inr, expires_at, is_used, created_at)
        VALUES (?, ?, 0.0, ?, 0, ?)
    """, (nonce, max_spend_inr, expires_at, now.isoformat()))
    conn.commit()
    conn.close()

    add_audit_log(
        action="MANDATE_CONFIGURED",
        policy_verdict="ALLOWED",
        details=f"New mandate {nonce} generated. Max spend: ₹{max_spend_inr:,.2f}, Expiration: {expires_at}"
    )

    return {
        "nonce": nonce,
        "max_spend_inr": max_spend_inr,
        "current_spend_inr": 0.0,
        "expires_at": expires_at,
        "is_used": 0,
        "created_at": now.isoformat()
    }

def add_mandate_spend(nonce: str, amount: float) -> dict:
    """
    Cumulative spend update: adds approved transaction amount to current_spend_inr.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM intent_mandates WHERE nonce = ?", (nonce,))
    row = cursor.fetchone()
    if row:
        mandate = dict(row)
        old_spend = mandate.get("current_spend_inr", 0.0)
        new_spend = old_spend + amount
        max_spend = mandate.get("max_spend_inr", 0.0)
        is_used = 1 if new_spend >= max_spend else mandate.get("is_used", 0)
        
        cursor.execute("""
            UPDATE intent_mandates
            SET current_spend_inr = ?, is_used = ?
            WHERE nonce = ?
        """, (new_spend, is_used, nonce))
        conn.commit()

        add_audit_log(
            action="CUMULATIVE_SPEND_UPDATED",
            policy_verdict="ALLOWED",
            details=f"Mandate {nonce} cumulative spend updated: ₹{old_spend:,.2f} + ₹{amount:,.2f} = ₹{new_spend:,.2f} of ₹{max_spend:,.2f} ceiling."
        )
    conn.close()
    return get_mandate(nonce)

def mark_mandate_used(nonce: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE intent_mandates SET is_used = 1 WHERE nonce = ?", (nonce,))
    conn.commit()
    conn.close()

def revoke_mandate(nonce: str) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE intent_mandates SET is_used = -1 WHERE nonce = ?", (nonce,))
    conn.commit()
    cursor.execute("SELECT * FROM intent_mandates WHERE nonce = ?", (nonce,))
    row = cursor.fetchone()
    conn.close()

    add_audit_log(
        action="MANDATE_REVOKED",
        policy_verdict="MANDATE_REVOKED",
        details=f"EMERGENCY KILL SWITCH ACTIVATED: Intent mandate {nonce} has been REVOKED by user."
    )

    if row:
        return dict(row)
    return {
        "nonce": nonce,
        "max_spend_inr": 0.0,
        "current_spend_inr": 0.0,
        "expires_at": "",
        "is_used": -1,
        "created_at": ""
    }

if __name__ == "__main__":
    init_db(force_recreate=True)
    print("Database recreated and re-seeded with Cumulative Spend support successfully.")
