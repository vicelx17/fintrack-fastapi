from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user model with common fields for user operations."""

    username: str = Field(
        ...,
        description="Unique username for the user account.",
        examples=["vicelx_dev"],
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_]+$"  # Only alphanumeric and underscores
    )
    email: EmailStr = Field(
        ...,
        description="User's email address. Must be a valid email format.",
        examples=["vicelx.dev@example.com"]
    )
    role: str = Field(
        default="user",
        description="User role in the system. Determines access permissions.",
        examples=["user", "admin"]
    )


class UserCreate(UserBase):
    """Schema for creating a new user account."""

    password: str = Field(
        ...,
        description="User's password. Should be strong and secure.",
        examples=["SecurePassword123!"],
        min_length=8,
        max_length=128
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user. All fields are optional."""

    username: Optional[str] = Field(
        None,
        description="Updated username for the user account.",
        examples=["vicelx_dev_updated"],
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_]+$"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Updated email address for the user.",
        examples=["vicelx.updated@example.com"]
    )
    password: Optional[str] = Field(
        None,
        description="Updated password for the user account.",
        examples=["NewSecurePassword123!"],
        min_length=8,
        max_length=128
    )
    role: Optional[str] = Field(
        None,
        description="Updated role for the user. Only admins can change roles.",
        examples=["user", "admin"]
    )


class UserResponse(UserBase):
    """Schema for user responses, including database fields."""

    id: int = Field(
        ...,
        description="Unique identifier for the user.",
        examples=[1]
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active.",
        examples=[True]
    )

    class Config:
        from_attributes = True