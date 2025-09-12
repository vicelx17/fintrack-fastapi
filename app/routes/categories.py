from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.category import CategoryResponse, CategoryCreate, CategoryUpdate
from app.services.auth_service import get_current_user
from app.services.categories_service import get_categories, create_category, get_category_by_id, update_category, \
    delete_category

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/",
            response_model=List[CategoryResponse],
            status_code=status.HTTP_200_OK,
            summary="List categories",
            description="Return all authenticated user categories."
            )
async def list_categories(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_categories(db, current_user.id)


@router.get("/{id}",
            response_model=CategoryResponse,
            status_code=status.HTTP_200_OK,
            summary="Get a specific category by ID",
            description="Return a specific category by ID."
            )
async def list_category_by_id(
        id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await get_category_by_id(db, current_user.id, id)


@router.post("/",
             response_model=CategoryResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create new category",
             description="Allows user to create a category."
             )
async def create_new_category(
        category: CategoryCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await create_category(db, current_user.id, category)


@router.put("/{id}",
            response_model=CategoryResponse,
            summary="Update a category",
            description="Allows user to update a category.")
async def update_user_category(
        id: int,
        category: CategoryUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    updated_category = await update_category(db, current_user.id, id, category)
    if not updated_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return updated_category


@router.delete("/{id}",
               summary="Delete a category",
               description="Allows user to delete a category and all of the associated transactions.")
async def delete_user_category(
        id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await delete_category(db, current_user.id, id)
