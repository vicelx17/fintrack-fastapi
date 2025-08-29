from datetime import date
from typing import Optional

from pydantic import BaseModel, model_validator, ConfigDict


class BudgetBase(BaseModel):
    amount: float
    start_date: date
    end_date: date
    category_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= before end_date")
        return self

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[int] = None

class BudgetResponse(BudgetBase):
    id: int
    user_id: int

    class Config:
        from_attributes: True