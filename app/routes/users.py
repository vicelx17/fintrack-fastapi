from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.auth_service import get_current_user, require_admin
from app.services.user_service import get_all_users, get_user_by_id, update_user, delete_user
from app.core.database import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/",
            summary="Retrieve all users in the system",
            description="This endpoint is restricted to administrators only. Returns a list of all registered users in the system with their basic information.",
            response_model=List[UserResponse], dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await get_all_users(db)

@router.get("/me",
            summary="Retrieve the current authenticated user's profile.",
            description="Returns the profile information for the currently authenticated user. This endpoint allows users to view their own profile data.",
            response_model=UserResponse)
async def get_current_user_profile(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    return await get_user_by_id(db, current_user.id)
@router.put("/me",
            summary="Update the current authenticated user's profile.",
            description="Allows users to update their own profile information. Only the fields provided in the request body will be updated.",
            response_model=UserResponse)
async def update_current_user_profile(
        user_data: UserUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    return await update_user(db, current_user.id, user_data)

@router.delete("/me",
               summary="Delete the current authenticated user's account.",
               description="Permanently deletes the current user's account and all associated data. This action is irreversible.",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user_account(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await delete_user(db, current_user.id)
    return {"message": "Account deleted successfully"}


@router.get("/{user_id}",
            summary="Retrieve a specific user by ID (Admin only).",
            description="Allows administrators to retrieve any user's profile information by their ID.",
            response_model=UserResponse,
            dependencies=[Depends(require_admin)])
async def get_user_by_id_endpoint(
        user_id: int,
        db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}",
            summary="Update a specific user by ID (Admin only).",
            description="Allows administrators to update any user's profile information. Only the fields provided in the request body will be updated.",
            response_model=UserResponse,
            dependencies=[Depends(require_admin)])
async def update_user_by_id(
        user_id: int,
        user_data: UserUpdate,
        db: AsyncSession = Depends(get_db)
):
    updated_user = await update_user(db, user_id, user_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user

@router.delete("/{user_id}",
               summary="Delete a specific user by ID (Admin only).",
               description="Allows administrators to delete any user's account and all associated data. This action is irreversible.",
               dependencies=[Depends(require_admin)], status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
        user_id: int,
        db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    result = await delete_user(db, user_id)
    return {"message": "User deleted successfully"}