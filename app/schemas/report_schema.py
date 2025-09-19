from datetime import date
from typing import List

from pydantic import BaseModel, Field


class ReportCategory(BaseModel):
    """Represents a financial report category, including its net balance."""
    category: str = Field(
        ...,
        description="Name of the category. Example: 'Food', 'Transportation'.",
        examples=["Food"]
    )
    net_category_balance: float = Field(
        ...,
        description="Net balance for this category. Positive values indicate income, negative values indicate expenses.",
        examples=[-250.75]
    )


class ReportTransaction(BaseModel):
    """ Represents an individual transaction included in the report. """
    id: int = Field(
        ...,
        description="Unique identifier for the transaction.",
        examples=[123]
    )
    amount: float = Field(
        ...,
        description="Transaction amount. Positive values for income, negative values for expenses.",
        examples=[-50.00]
    )
    description: str = Field(
        ...,
        description="Description or details of the transaction.",
        examples=["Gasoline payment"]
    )
    report_date: date = Field(
        ...,
        description="Date when the transaction was recorded.",
        examples=["2025-09-19"]
    )
    category: str = Field(
        ...,
        description="Category to which the transaction belongs.",
        examples=["Transportation"]
    )

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    """
    Represents the complete financial report response,
    including totals, top categories, and detailed transactions.
    """
    total_income: float = Field(
        ...,
        description="Total sum of all income within the report period.",
        examples=[4500.00]
    )
    total_expenses: float = Field(
        ...,
        description="Total sum of all expenses within the report period.",
        examples=[3200.50]
    )
    net_balance: float = Field(
        ...,
        description="Net balance calculated as (total_income - total_expenses).",
        examples=[1299.50]
    )
    top_categories: List[ReportCategory] = Field(
        ...,
        description="List of categories with their respective net balances, ordered by relevance.",
        examples=[[
            {"category": "Food", "net_category_balance": -250.75},
            {"category": "Transportation", "net_category_balance": -100.00}
        ]]
    )
    transactions: List[ReportTransaction] = Field(
        ...,
        description="Detailed list of all transactions included in the report.",
        examples=[[
            {
                "id": 1,
                "amount": -50.00,
                "description": "Gasoline payment",
                "report_date": "2025-09-19",
                "category": "Transportation"
            },
            {
                "id": 2,
                "amount": 1200.00,
                "description": "Salary payment",
                "report_date": "2025-09-18",
                "category": "Income"
            }
        ]]
    )

    class Config:
        from_attributes = True