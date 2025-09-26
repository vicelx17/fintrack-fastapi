from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.schemas.auth_schema import LoginBody, RegisterBody, TokenResponse
from app.services.auth_service import login_user, get_current_user
from app.services.user_service import register_user
from app.core.database import get_db
from app.models.user import User

router = APIRouter(tags=["Authentication"])

@router.get("/me",
            summary="Get current authenticated user information.",
            description="Returns basic information about the currently authenticated user based on their JWT token.",
            response_model=dict)
async def read_current_user(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active
    }

@router.post("/register",
             summary="Register a new user account.",
             description="Creates a new user account with the provided credentials and returns an access token for immediate authentication.",
             response_model=TokenResponse)
async def register_new_user(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    user = await register_user(db,body.first_name,body.last_name, body.username, body.email, body.password, body.role)
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login",
             summary="Authenticate user and obtain access token.",
             description="Validates user credentials and returns an access token if authentication is successful. The token can be used for subsequent API requests.",
             response_model=TokenResponse)
async def login_user_endpoint(data: LoginBody, db: AsyncSession = Depends(get_db)):
    return await login_user(data.username, data.password, db)
