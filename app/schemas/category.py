from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(..., example="Food", description="Name of category.")

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    name: str | None = Field(None, example="Kitchen", description="New name of category.")
    pass

class CategoryResponse(CategoryBase):
    id: int = Field(..., example=1,description="ID of category")
    user_id: int = Field(...,description="User ID")
    transaction_count: int = Field(...,description="Associated category transactions count")
    model_config = {"from_attributes":True}
