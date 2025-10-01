from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

class TransactionStatsResponse(BaseModel):
    """Base schema for transaction stats response"""
    totalTransactions: int = Field(...,example=3, description="Total user transactions.")
    totalIncome: float = Field(...,example=45.0, description="Total transaction incomes.")
    totalExpenses: float = Field(..., example=40.0, description="Total transaction expenses.")
    averageDaily: float = Field(...,examples=12.4, description="Average daily net balance.")

class TransactionFilters(BaseModel):
    search: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    dateRange: Optional[str] = None
    account: Optional[str] = None
    minAmount: Optional[float] = None
    maxAmount: Optional[float] = None

class TransactionBase(BaseModel):
    """Base schema for transaction operations"""
    amount: float = Field(..., example=50.0, description="Transaction amount")
    description: Optional[str] = Field(default=None, example="Supermarket shopping", description="Transaction description")
    category_id: Optional[int] = Field(default=None, example=1, description="ID of associated category")
    type: str = Field(...,example="income", description="Transaction type")
    notes: Optional[str] = Field(default=None,example="Bought: 3 eggs and 1 pack of milk.", description="Aditional transaction notes")

class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction"""
    transaction_date: date = Field(...,example="2025-09-09", description="Date of the transaction")
    pass

class TransactionUpdate(TransactionBase):
    """Schema for updating an existing transaction"""
    amount: Optional[float] = Field(default=None, example=75.0, description="Updated transaction amount")
    description: Optional[str] = Field(default=None, example="Updated description", description="Updated description")
    category_id: Optional[int] = Field(default=None, example=2, description="Updated category ID")
    type: str = Field(..., example="income", description="Transaction type")
    notes: Optional[str] = Field(default=None, example="Bought: 3 eggs and 1 pack of milk.",description="Aditional transaction notes")
    pass

class TransactionResponse(TransactionBase):
    """Schema for transaction response"""
    id: int = Field(..., example=1, description="Transaction unique identifier")
    user_id: int = Field(..., example=123, description="ID of the transaction owner")
    type: str = Field(..., example="income", description="Transaction type")
    notes: Optional[str] = Field(default=None, example="Bought: 3 eggs and 1 pack of milk.", description="Aditional transaction notes")
    transaction_date: date = Field(...,example="2025-09-09", description="Date of the transaction")


    model_config = {"from_attributes": True}