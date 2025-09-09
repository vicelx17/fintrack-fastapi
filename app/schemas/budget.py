from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, model_validator, ConfigDict


class BudgetBase(BaseModel):
    name: str
    amount: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None:
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
    name: str
    amount: float
    id: int
    user_id: int

    class Config:
        from_attributes: True