from pydantic import BaseModel
from typing import Optional, List

class CostRow(BaseModel):
    provider: str
    environment: Optional[str] = None
    service: Optional[str] = None
    date: str
    cost_amount: float
    cost_currency: str = "USD"

class CostResponse(BaseModel):
    rows: List[CostRow]
    total: float
    currency: str
