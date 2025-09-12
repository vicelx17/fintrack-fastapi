from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    """Base schema for transaction operations"""
    amount: float = Field(..., example=50.0, description="Transaction amount: positive for income, negative for expenses")
    description: Optional[str] = Field(default=None, example="Supermarket shopping", description="Transaction description")
    category_id: Optional[int] = Field(default=None, example=1, description="ID of associated category")

class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction"""
    pass

class TransactionUpdate(TransactionBase):
    """Schema for updating an existing transaction"""
    amount: Optional[float] = Field(default=None, example=75.0, description="Updated transaction amount")
    description: Optional[str] = Field(default=None, example="Updated description", description="Updated description")
    category_id: Optional[int] = Field(default=None, example=2, description="Updated category ID")
    pass

class TransactionResponse(TransactionBase):
    """Schema for transaction response"""
    id: int = Field(..., example=1, description="Transaction unique identifier")
    user_id: int = Field(..., example=123, description="ID of the transaction owner")
    transaction_date: date = Field(...,example="2025-09-09", description="Date of the transaction")

    model_config = {"from_attributes": True}
