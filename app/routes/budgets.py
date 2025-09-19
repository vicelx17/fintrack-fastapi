# app/api/v1/budget_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services.auth_service import get_current_user
from app.services.budget_service import (
    create_budget,
    get_budgets,
    get_budget_by_id,
    update_budget,
    delete_budget
)

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("/",
            summary="Retrieve all budgets for the authenticated user.",
            description="Returns a list of all budgets belonging to the current user including their details such as name, amount, dates, and category.",
            response_model=List[BudgetResponse])
async def list_budgets(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return await get_budgets(db, current_user.id)

@router.get("/{budget_id}",
            summary="Retrieve a specific budget by its ID.",
            description="Returns detailed information about a specific budget if it belongs to the authenticated user.",
            response_model=BudgetResponse)
async def list_budget_by_id(
        budget_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    budget = await get_budget_by_id(db, current_user.id, budget_id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    return budget


@router.post("/",
             summary= "Create a new budget for the authenticated user.",
             description= "Creates a new budget with the provided information. The budget will be associated with the current authenticated user.",
             response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_new_budget(
        budget: BudgetCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return await create_budget(db, current_user.id, budget)


@router.put("/{budget_id}",
            summary="Update an existing budget",
            description="Updates the specified budget with the provided information. Only the fields included in the request body will be updated",
            response_model=BudgetResponse)
async def update_user_budget(
        budget_id: int,
        budget_update: BudgetUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    updated_budget = await update_budget(db, current_user.id, budget_id, budget_update)
    if not updated_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    return updated_budget


@router.delete("/{budget_id}",
               summary="Delete a specific budget",
               description="Permanently delete the specified budget if it belongs to the authenticated user.",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_budget(
        budget_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    budget = await get_budget_by_id(db, current_user.id, budget_id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    result = await delete_budget(db, current_user.id, budget_id)
    return {"message": "Budget deleted successfully"}