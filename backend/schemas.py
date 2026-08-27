from pydantic import BaseModel, Field
from typing import Optional, List

class MandateConfig(BaseModel):
    max_spend_inr: float = Field(..., gt=0, description="Maximum spending limit in INR")
    duration_minutes: int = Field(default=60, gt=0, description="Duration in minutes before mandate expires")

class MandateResponse(BaseModel):
    nonce: str
    max_spend_inr: float
    current_spend_inr: float = 0.0
    expires_at: str
    is_used: int
    created_at: str

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User prompt or buying instruction")
    mandate_nonce: Optional[str] = Field(default=None, description="Optional override for active mandate nonce")

class AuditLog(BaseModel):
    id: int
    timestamp: str
    action: str
    policy_verdict: str
    details: str

class ChatResponse(BaseModel):
    response_text: str
    action_taken: str
    policy_verdict: str
    razorpay_order_id: Optional[str] = None
    quote: Optional[dict] = None
    audit_logs: List[AuditLog] = []

class CatalogItem(BaseModel):
    item_id: str
    name: str
    price_inr: float
    stock: int
    delivery_days: int
    description: Optional[str] = ""

class QuoteRequest(BaseModel):
    item_id: str
    quantity: int = 1

class QuoteResponse(BaseModel):
    quote_id: str
    item_id: str
    item_name: str
    price_inr: float
    quantity: int
    total_amount_inr: float
    stock_available: bool

class CheckoutRequest(BaseModel):
    quote_id: str
    mandate_nonce: str
