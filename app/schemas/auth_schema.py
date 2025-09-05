from typing import Optional

from pydantic import BaseModel

class LoginBody(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterBody(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = None