from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class LoginBody(BaseModel):
    """Schema for user login requests."""

    username: str = Field(
        ...,
        description="Username for authentication.",
        examples=["vicelx_dev"],
        min_length=3,
        max_length=50
    )
    password: str = Field(
        ...,
        description="User's password for authentication.",
        examples=["SecurePassword123!"],
        min_length=8,
        max_length=128
    )


class TokenResponse(BaseModel):
    """Schema for authentication token responses."""

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication."
    )
    token_type: str = Field(
        default="bearer",
        description="Type of the authentication token.",
        examples=["bearer"]
    )

class RegisterBody(BaseModel):
    """Schema for user registration requests."""
    first_name: str = Field(
        ...,
        description="First name of the user.",
        examples=["Peter"],
        min_length=3,
        max_length=50,
    )
    last_name: str = Field(
        ...,
        description="Last name of the user.",
        examples=["Parker"],
        min_length=3,
        max_length=50,
    )

    username: str = Field(
        ...,
        description="Desired username for the new account. Must be unique.",
        examples=["vicelx_dev"],
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_]+$"  # Only alphanumeric and underscores
    )
    email: str = Field(
        ...,
        description="Email address for the new account. Must be unique and valid.",
        examples=["vicelx.dev@example.com"]
    )
    password: str = Field(
        ...,
        description="Password for the new account. Should be strong and secure.",
        examples=["SecurePassword123!"],
        min_length=8,
        max_length=128
    )
    role: Optional[str] = Field(
        default="user",
        description="Role to assign to the new user. Defaults to 'user' if not specified.",
        examples=["user", "admin"]
    )