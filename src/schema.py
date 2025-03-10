# Models with validation
from pydantic import BaseModel

# API request models
class TransferRequest(BaseModel):
    transaction_id: str
    transfers_dict: dict[str, float]


class TransferResponse(BaseModel):
    transaction_id: str
    status: str
    message: str