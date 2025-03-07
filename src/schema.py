# Models with validation
from pydantic import BaseModel

# API request models
class TransferRequest(BaseModel):
    miner_coldkey: str
    amount_in_usd: float
    billing_history_id: str

class TransferResponse(BaseModel):
    billing_history_id: str
    status: str
    message: str