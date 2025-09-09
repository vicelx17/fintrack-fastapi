from datetime import datetime
from typing import List

from pydantic import BaseModel


class ReportCategory(BaseModel):
    category: str
    total: float

class ReportTransaction(BaseModel):
    id: int
    amount: float
    description: str
    date: datetime
    category: str

    class Config:
        from_attributes = True

class ReportResponse(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    top_categories: List[ReportCategory]
    transactions: List[ReportTransaction]

    class Config:
        from_attributes = True
