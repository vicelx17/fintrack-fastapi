from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetUpdate


async def create_budget(db:AsyncSession, user_id:int, budget: BudgetCreate):
    new_budget = Budget(
        user_id = user_id,
        amount = budget.amount,
        category = budget.category_id,
        start_date = budget.start_date,
        end_date = budget.end_date,
    )
    db.add(new_budget)
    await db.commit()
    await db.refresh(new_budget)
    return new_budget

async def get_budgets(db:AsyncSession, user_id:int):
    result = await db.execute(select(Budget).where(Budget.user_id == user_id))

async def get_budget_by_id(db:AsyncSession, user_id:int, budget_id:int):
    result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    return result.scalars().one_or_none()

async def update_budget(db:AsyncSession, user_id:int, budget_id:int, budget_update:BudgetUpdate):
    query = (
        update(Budget)
        .where(Budget.id == Budget.id, Budget.user_id == user_id)
        .values(budget_update.model_dump(exclude_unset=True))
        .returning(Budget)
    )
    result = await db.execute(query)
    await db.commit()
    return result.scalars().one_or_none()

async def delete_budget(db:AsyncSession, user_id:int, budget_id:int):
    query = (delete(Budget).where(Budget.id == budget_id, Budget.user_id == user_id))
    await db.execute(query)
    await db.commit()
    return {"message": "budget deleted"}