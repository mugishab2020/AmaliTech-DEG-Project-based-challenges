from pydantic import BaseModel


class PaymentRequest(BaseModel):
    amount: float
    currency: str


class PaymentResponse(BaseModel):
    message: str
    amount: float
    currency: str
    transaction_id: str
    processed_at: float