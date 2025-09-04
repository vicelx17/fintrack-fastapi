from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.auth_service import get_current_user
from app.services.user_service import get_all_users, get_user_by_id, update_user, delete_user
from app.core.database import get_db

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await get_all_users(db)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_user_by_id(db, current_user.id)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user_data(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await update_user(db, current_user.id, user_data)

@router.delete("/{user_id}")
async def delete_user_data(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await delete_user(db, current_user.id)
