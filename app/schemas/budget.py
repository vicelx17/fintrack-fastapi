from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, Field, model_validator


class BudgetBase(BaseModel):
    """Base budget model with common fields for budget operations."""

    name: str = Field(
        ...,
        description="Name of the budget.",
        examples=["Monthly Food Budget"],
        min_length=1,
        max_length=100
    )
    amount: float = Field(
        ...,
        description="Budget amount limit. Must be positive.",
        examples=[1000.00],
        gt=0
    )
    start_date: Optional[date] = Field(
        None,
        description="Start date for the budget period. If not provided, budget has no start date restriction.",
        examples=["2025-01-01"]
    )
    end_date: Optional[date] = Field(
        None,
        description="End date for the budget period. If not provided, budget has no end date restriction.",
        examples=["2025-12-31"]
    )
    period: Literal["weekly", "monthly", "quarterly", "yearly"] = Field(
        "monthly",
        description="Budget period type.",
        examples=["monthly"]
    )
    alert_threshold: int = Field(
        80,
        description="Alert threshold percentage (0-100).",
        examples=[80],
        ge=0,
        le=100
    )
    category_id: Optional[int] = Field(
        None,
        description="ID of the category this budget applies to. If not provided, applies to all categories.",
        examples=[1],
        gt=0
    )

    @model_validator(mode="after")
    def validate_dates(self):
        """Validate that start_date is not after end_date."""
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before or equal to end_date")
        return self


class BudgetCreate(BudgetBase):
    """Schema for creating a new budget."""
    pass


class BudgetUpdate(BaseModel):
    """Schema for updating an existing budget. All fields are optional."""

    name: Optional[str] = Field(
        None,
        description="Updated name of the budget.",
        examples=["Updated Monthly Food Budget"],
        min_length=1,
        max_length=100
    )
    amount: Optional[float] = Field(
        None,
        description="Updated budget amount limit. Must be positive.",
        examples=[1200.00],
        gt=0
    )
    start_date: Optional[date] = Field(
        None,
        description="Updated start date for the budget period.",
        examples=["2025-02-01"]
    )
    end_date: Optional[date] = Field(
        None,
        description="Updated end date for the budget period.",
        examples=["2025-12-31"]
    )
    period: Optional[Literal["weekly", "monthly", "quarterly", "yearly"]] = Field(
        None,
        description="Updated budget period type.",
        examples=["monthly"]
    )
    alert_threshold: Optional[int] = Field(
        None,
        description="Updated alert threshold percentage (0-100).",
        examples=[80],
        ge=0,
        le=100
    )
    category_id: Optional[int] = Field(
        None,
        description="Updated category ID this budget applies to.",
        examples=[2],
        gt=0
    )

    @model_validator(mode="after")
    def validate_dates(self):
        """Validate that start_date is not after end_date when both are provided."""
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before or equal to end_date")
        return self


class BudgetResponse(BaseModel):
    """Schema for budget responses, including database fields."""

    id: int
    userId: int
    category: str
    budgetAmount: float
    spentAmount: float
    period: str
    startDate: str
    endDate: str
    alertThreshold: int
    status: Literal["good", "warning", "over"]

    class Config:
        from_attributes = True