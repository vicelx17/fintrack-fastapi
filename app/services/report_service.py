from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.report_schema import ReportResponse, ReportTransaction, ReportCategory


async def generate_report(db:AsyncSession ,user_id: int,days: int) -> ReportResponse:
    """
    Genera un reporte financiero para el usuario autenticado.
    :param days: numero de días hacia atras desde hoy
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    result = await db.execute(
        select(Transaction, Category.name)
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= now,
        )
        .order_by(Transaction.date.desc())
    )
    transactions_data = result.all()

    if not transactions_data:
        return ReportResponse(
            total_income=0.0,
            total_expenses=0.0,
            net_balance=0.0,
            top_categories=[],
            transactions=[]
        )

    total_income = 0.0,
    total_expenses = 0.0,
    transactions_list: List[ReportTransaction] = []

    category_totals = {}

    for transaction, category_name in transactions_data:
        if transaction.amount >= 0:
            total_income += transaction.amount
        else:
            total_expenses += abs(transaction.amount)

        if category_name not in category_totals:
            category_totals[category_name] = 0.0
        category_totals[category_name] += abs(transaction.amount)

        transactions_list.append(ReportTransaction(
            id=transaction.id,
            amount=transaction.amount,
            description=transaction.description,
            date=transaction.date,
            category=category_name,
        )
    )

    top_categories_list = sorted(
        [ReportCategory(category = k, total = v) for k, v in category_totals.items()],
        key = lambda x: x.total,
        reverse = True
    )[:3]

    # Final response
    return ReportResponse(
        total_income=round(total_income,2),
        total_expenses=round(total_expenses,2),
        net_balance=round(total_income - total_expenses,2),
        top_categories=top_categories_list,
        transactions=transactions_list
    )