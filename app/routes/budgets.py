from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict

from app.core.database import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services.auth_service import get_current_user
from app.services.budget_metrics_service import get_category_spending_breakdown, get_budget_performance, \
    get_budget_analytics, get_budget_overview, get_budget_alerts
from app.services.budget_service import (
    create_budget,
    get_budgets,
    get_budget_by_id,
    update_budget,
    delete_budget
)

router = APIRouter(prefix="/budgets", tags=["Budgets"])

# ============= GET ROUTES Endpoints =============

@router.get("/",
            summary="Retrieve all budgets for the authenticated user.",
            description="Returns a list of all budgets belonging to the current user including their details such as name, amount, dates, and category.",
            response_model=List[BudgetResponse])
async def list_budgets(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return await get_budgets(db, current_user.id)

@router.get("/alerts",
            summary="Get budget alerts",
            description="Returns all active budget alerts for the authenticated user, including exceeded budgets and approaching limits.")
async def list_budget_alerts(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    alerts = await get_budget_alerts(db, current_user.id)
    return {"alerts": alerts}


@router.get("/overview",
            summary="Get budget overview",
            description="Returns overall budget metrics including total budget, spent amount, and exceeded budgets.")
async def get_overview(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    overview = await get_budget_overview(db, current_user.id)
    return {"overview": overview}


@router.get("/analytics",
            summary="Get detailed budget analytics",
            description="Returns comprehensive budget analytics including overview, category breakdown, alerts, and trends.")
async def get_analytics(
        period: Optional[str] = Query("monthly", description="Period for analytics: weekly, monthly, quarterly, yearly"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    analytics = await get_budget_analytics(db, current_user.id, period)
    return {"analytics": analytics}


@router.get("/category-breakdown",
            summary="Get category spending breakdown",
            description="Returns spending breakdown by category for the current period.")
async def get_breakdown(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    breakdown = await get_category_spending_breakdown(db, current_user.id)
    return {"breakdown": breakdown}


@router.get("/performance/metrics",
            summary="Get budget performance metrics",
            description="Returns performance metrics for each budget including spending pace and days remaining.")
async def get_performance(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    performance = await get_budget_performance(db, current_user.id)
    return {"performance": performance}

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


@router.delete("/{id}",
               response_model=Dict,
               summary="Delete a specific budget",
               description="Permanently delete the specified budget if it belongs to the authenticated user.",
               )
async def delete_user_budget(
        id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return await delete_budget(db, current_user.id, id)