import asyncio
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from database import (
    init_db,
    get_db_connection,
    get_recent_audit_logs,
    get_active_mandate,
    set_mandate,
    revoke_mandate,
    add_audit_log
)
from schemas import (
    MandateConfig,
    MandateResponse,
    ChatRequest,
    ChatResponse
)
from agent import AgentOrchestrator

app = FastAPI(
    title="Razorpay Agentic Commerce API",
    description="Backend API for Razorpay AI Buildathon 2026 (Track 01) with Declarative Policy Hooks and Real-time Audit Trail.",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = AgentOrchestrator()

@app.on_event("startup")
def on_startup():
    init_db()
    print("🚀 Database initialized in SQLite WAL mode.")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Razorpay Agentic Commerce Engine",
        "track": "Track 01 - AI Growth & Agentic Commerce",
        "policy_engine": "Google Antigravity Declarative Hooks",
        "database": "SQLite (WAL Mode)"
    }

@app.get("/api/catalog")
def get_catalog():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM merchants_catalog")
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return items

@app.post("/api/mandate", response_model=MandateResponse)
def update_mandate(config: MandateConfig):
    res = set_mandate(config.max_spend_inr, config.duration_minutes)
    return res

@app.post("/api/mandate/refresh", response_model=MandateResponse)
def refresh_mandate_endpoint(config: MandateConfig):
    res = set_mandate(config.max_spend_inr, config.duration_minutes)
    add_audit_log(
        action="MANDATE_REFRESHED",
        policy_verdict="ALLOWED",
        details=f"Fresh intent authorization mandate generated: {res['nonce']} with max spend cap ₹{config.max_spend_inr:,.2f}."
    )
    return res

@app.post("/api/mandate/revoke", response_model=MandateResponse)
def revoke_mandate_endpoint(req: dict = None):
    nonce_to_revoke = req.get("nonce") if req else None
    if not nonce_to_revoke:
        active_m = get_active_mandate()
        if not active_m:
            raise HTTPException(status_code=404, detail="No active mandate found to revoke.")
        nonce_to_revoke = active_m["nonce"]
    
    res = revoke_mandate(nonce_to_revoke)
    return res

@app.get("/api/mandate", response_model=MandateResponse)
def fetch_mandate():
    mandate = get_active_mandate()
    if not mandate:
        raise HTTPException(status_code=404, detail="No active mandate found.")
    return mandate

@app.post("/api/chat", response_model=ChatResponse)
def handle_chat(req: ChatRequest):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    # Process agent loop & policy guardrails
    result = agent.process_prompt(req.prompt, req.mandate_nonce)
    
    # Fetch recent audit logs to return in payload
    recent_logs = get_recent_audit_logs(limit=20)
    
    return ChatResponse(
        response_text=result["response_text"],
        action_taken=result["action_taken"],
        policy_verdict=result["policy_verdict"],
        razorpay_order_id=result.get("razorpay_order_id"),
        quote=result.get("quote"),
        audit_logs=recent_logs
    )

@app.get("/api/audit-logs")
def fetch_audit_logs(limit: int = 50):
    return get_recent_audit_logs(limit=limit)

@app.get("/api/audit-stream")
async def audit_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint streaming real-time SQLite audit log updates to the React terminal console.
    """
    async def log_generator():
        last_seen_id = 0
        last_event_id_hdr = request.headers.get("Last-Event-ID")
        if last_event_id_hdr and last_event_id_hdr.isdigit():
            last_seen_id = int(last_event_id_hdr)
        else:
            # Send initial batch of logs if first connection
            initial_logs = get_recent_audit_logs(limit=10)
            if initial_logs:
                last_seen_id = max(log["id"] for log in initial_logs)
                for log in reversed(initial_logs):
                    yield {
                        "id": str(log["id"]),
                        "event": "audit_event",
                        "data": json.dumps(log)
                    }

        while True:
            if await request.is_disconnected():
                break

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs WHERE id > ? ORDER BY id ASC", (last_seen_id,))
            new_logs = [dict(r) for r in cursor.fetchall()]
            conn.close()

            for log in new_logs:
                last_seen_id = max(last_seen_id, log["id"])
                yield {
                    "id": str(log["id"]),
                    "event": "audit_event",
                    "data": json.dumps(log)
                }

            await asyncio.sleep(0.5)

    return EventSourceResponse(log_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
