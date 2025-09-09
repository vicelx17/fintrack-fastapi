from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction
from app.schemas.report_schema import ReportResponse, ReportTransaction, ReportCategory


async def generate_report(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None) -> ReportResponse:

    query = select(Transaction).options(selectinload(Transaction.category)).where(Transaction.user_id == user_id)

    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)

    result = await db.execute(query)
    transactions_data = result.scalars().all()

    if not transactions_data:
        return ReportResponse(
            total_income=0.0,
            total_expenses=0.0,
            net_balance=0.0,
            top_categories=[],
            transactions=[]
        )

    total_income = sum(t.amount for t in transactions_data if t.amount > 0)
    total_expenses = sum(abs(t.amount) for t in transactions_data if t.amount < 0)
    net_balance = total_income - total_expenses

    category_totals = {}

    for transaction in transactions_data:
        category_name = transaction.category.name if transaction.category else "Sin categoría"
        category_totals[category_name] = category_totals.get(category_name, 0) + abs(transaction.amount)

    top_categories = sorted(
        [ReportCategory(category=name, total=total) for name, total in category_totals.items()],
        key=lambda c: c.total,
        reverse=True
    )[:3]

    transactions_list = [
        ReportTransaction(
            id=transaction.id,
            amount=transaction.amount,
            description=transaction.description,
            date=transaction.date,
            category=transaction.category.name if transaction.category else "Sin categoría",
        )
        for transaction in transactions_data
    ]

    # Final response
    return ReportResponse(
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        top_categories=top_categories,
        transactions=transactions_list
    )