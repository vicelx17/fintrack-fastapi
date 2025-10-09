from typing import Dict, List
from sqlalchemy import update, delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetUpdate


async def calculate_spent_amount(
        db: AsyncSession,
        user_id: int,
        category_id: int,
        start_date: date,
        end_date: date
) -> float:
    """Calculate total spent amount for a category within a date range."""
    result = await db.execute(
        select(func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.type == "expense"
        )
    )
    total = result.scalar()
    return float(total) if total else 0.0


def calculate_status(spent_amount: float, budget_amount: float, alert_threshold: int) -> str:
    """Calculate budget status based on spent amount and threshold."""
    if abs(spent_amount) > budget_amount:
        return "over"

    percentage = (abs(spent_amount) / budget_amount) * 100
    if percentage >= alert_threshold:
        return "warning"

    return "good"


async def budget_to_dict(db: AsyncSession, budget: Budget) -> Dict:
    """Convert Budget model to dictionary with calculated fields."""
    category_result = await db.execute(
        select(Category).where(Category.id == budget.category_id)
    )
    category = category_result.scalar_one_or_none()

    spent_amount = await calculate_spent_amount(
        db,
        budget.user_id,
        budget.category_id,
        budget.start_date,
        budget.end_date
    )

    status = calculate_status(spent_amount, budget.amount, budget.alert_threshold)

    return {
        "id": budget.id,
        "userId": budget.user_id,
        "category": category.name if category else "Unknown",
        "budgetAmount": budget.amount,
        "spentAmount": abs(spent_amount),
        "period": budget.period,
        "startDate": budget.start_date.isoformat(),
        "endDate": budget.end_date.isoformat(),
        "alertThreshold": budget.alert_threshold,
        "status": status
    }

async def create_budget(db: AsyncSession, user_id: int, budget: BudgetCreate) -> Dict:
    """Create a new budget."""
    new_budget = Budget(
        user_id=user_id,
        name=budget.name,
        amount=budget.amount,
        category_id=budget.category_id,
        start_date=budget.start_date,
        end_date=budget.end_date,
        period=budget.period,
        alert_threshold=budget.alert_threshold,
    )
    db.add(new_budget)
    await db.commit()
    await db.refresh(new_budget)

    return await budget_to_dict(db, new_budget)

async def get_budgets(db: AsyncSession, user_id: int) -> List[Dict]:
    """Get all budgets for a user."""
    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id)
    )
    budgets = result.scalars().all()

    return [await budget_to_dict(db, budget) for budget in budgets]

async def get_budget_by_id(db: AsyncSession, user_id: int, budget_id: int) -> Dict | None:
    """Get a specific budget by ID."""
    result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    budget = result.scalar_one_or_none()

    if not budget:
        return None

    return await budget_to_dict(db, budget)

async def update_budget(
        db: AsyncSession,
        user_id: int,
        budget_id: int,
        budget_update: BudgetUpdate
) -> Dict | None:
    """Update an existing budget."""
    query = (
        update(Budget)
        .where(Budget.id == budget_id, Budget.user_id == user_id)
        .values(budget_update.model_dump(exclude_unset=True))
        .returning(Budget)
    )
    result = await db.execute(query)
    await db.commit()

    updated_budget = result.scalar_one_or_none()
    if not updated_budget:
        return None

    # Refresh para obtener las relaciones
    await db.refresh(updated_budget)
    return await budget_to_dict(db, updated_budget)

async def delete_budget(db: AsyncSession, user_id: int, budget_id: int) -> Dict:
    query = delete(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    result = await db.execute(query)
    await db.commit()

    if result.rowcount == 0:
        return {"success": False, "message": "Budget not found"}

    return {"success": True, "message": "Budget deleted"}