# app/api/v1/budget_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services.auth_service import get_current_user
from app.services.budget_service import (create_budget,get_budgets,get_budget_by_id,update_budget,delete_budget)

router = APIRouter(prefix="/budgets", tags=["Budgets"])

@router.get("/", response_model=list[BudgetResponse])
async def list_budgets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_budgets(db, current_user.id)


@router.get("/{budget_id}", response_model=BudgetResponse)
async def list_budget_by_id(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = await get_budget_by_id(db, current_user.id, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget

@router.post("/", response_model=BudgetResponse)
async def create_new_budget(
    budget: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_budget(db, current_user.id, budget)

@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_user_budget(
    budget_id: int,
    budget_update: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_budget = await update_budget(db, current_user.id, budget_id, budget_update)
    if not updated_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return updated_budget


@router.delete("/{budget_id}")
async def delete_user_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = await get_budget_by_id(db, current_user.id, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return await delete_budget(db, current_user.id, budget_id)
