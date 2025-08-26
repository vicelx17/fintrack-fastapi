from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.schemas.auth_schema import LoginBody, RegisterBody, TokenResponse
from app.services.auth_service import login_user, get_current_user
from app.services.user_service import register_user
from app.core.database import get_db
from app.models.User import User

router = APIRouter()

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}

@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    user = await register_user(db, body.username, body.email, body.password)
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginBody, db: AsyncSession = Depends(get_db)):
    return await login_user(data.username, data.password, db)


