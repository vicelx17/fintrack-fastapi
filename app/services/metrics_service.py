from datetime import date, timedelta
from typing import Dict, List

from sqlalchemy import func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction


async def calculate_financial_summary(db: AsyncSession, user_id: int) -> Dict:
    """
    Calculate financial summary for the dashboard
    """
    today = date.today()
    current_month_start = today.replace(day=1)

    if today.month == 1:
        previous_month_start = date(today.year - 1, 12, 1)
        previous_month_end = date(today.year - 1, 12, 31)
    else:
        previous_month_start = date(today.year, today.month - 1, 1)
        # Last day of the last month
        previous_month_end = current_month_start - timedelta(days=1)

        total_balance_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.user_id == user_id)
        )
        total_balance = total_balance_result.scalar() or 0.0

        # Current month incomes
        current_income_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.amount > 0,
                    Transaction.transaction_date >= current_month_start,
                )
            )
        )
        monthly_income = current_income_result.scalar() or 0.0

        # Current month expenses
        current_expenses_result = await db.execute(
            select(func.sum(func.abs(Transaction.amount)))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.amount < 0,
                    Transaction.transaction_date >= current_month_start,
                )
            )
        )
        monthly_expenses = current_expenses_result.scalar() or 0.0

        # Last month income
        previous_income_result = await db.execute(
            select(func.sum(func.abs(Transaction.amount)))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.amount > 0,
                    Transaction.transaction_date >= previous_month_start,
                    Transaction.transaction_date < previous_month_end,
                )
            )
        )
        previous_income = previous_income_result.scalar() or 0.0

        # Last month expenses
        previous_expenses_result = await db.execute(
            select(func.sum(func.abs(Transaction.amount)))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.amount < 0,
                    Transaction.transaction_date >= previous_month_start,
                    Transaction.transaction_date < previous_month_end,
                )
            )
        )
        previous_expenses = previous_expenses_result.scalar() or 0.0

        previous_balance = total_balance - (monthly_income - monthly_expenses)

        current_savings = monthly_income - monthly_expenses
        previous_savings = previous_income - previous_expenses

        def calculate_percentage_change(current: float, previous: float) -> str:
            if previous == 0:
                if current == 0:
                    return "0%"
                return "+100.0%" if current > 0 else "-100.0%"

            change = ((current - previous) / previous) * 100.0

            change = round(change, 1)
            return f"{'+' if change > 0 else ''}{change:.1f}%"

        balance_change = calculate_percentage_change(total_balance, previous_balance)
        income_change = calculate_percentage_change(monthly_income, previous_income)
        expenses_change = calculate_percentage_change(monthly_expenses, previous_expenses)
        savings_change = calculate_percentage_change(current_savings, previous_savings)

        return {
            "total_balance": round(total_balance, 2),
            "monthly_income": round(monthly_income, 2),
            "monthly_expenses": round(monthly_expenses, 2),
            "saving": round(current_savings, 2),
            "changes": {
                "balance": balance_change,
                "income": income_change,
                "expenses": expenses_change,
                "savings": savings_change,
            }
        }


async def get_monthly_chart_data(db: AsyncSession, user_id: int, months: int = 12) -> List[Dict]:
    """
    Obtain data for the monthly chart for de last 6 months
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    income_data = await db.execute(
        select(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.amount).label('ingresos')
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.amount > 0,
                Transaction.transaction_date >= start_date
            )
        )
        .group_by(
            extract('year', Transaction.transaction_date),
            extract('month', Transaction.transaction_date)
        )
    )

    expense_data = await db.execute(
        select(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(func.abs(Transaction.amount)).label('gastos')
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.amount < 0,
                Transaction.transaction_date >= start_date
            )
        )
        .group_by(
            extract('year', Transaction.transaction_date),
            extract('month', Transaction.transaction_date)
        )
    )

    months_map = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    income_dict = {}
    for row in income_data:
        key = (int(row.year), int(row.month))
        income_dict[key] = float(row.ingresos or 0)

    expense_dict = {}
    for row in expense_data:
        key = (int(row.year), int(row.month))
        expense_dict[key] = float(row.gastos or 0)

    # Combinar datos
    all_months = set(income_dict.keys()) | set(expense_dict.keys())
    data = []

    for year, month in sorted(all_months):
        month_name = months_map.get(month, str(month))
        incomes = income_dict.get((year, month), 0.0)
        expenses = expense_dict.get((year, month), 0.0)
        balance = incomes - expenses

        data.append({
            "month": month_name,
            "incomes": round(incomes, 2),
            "expenses": round(expenses, 2),
            "balance": round(balance, 2)
        })
    return data


async def get_category_chart_data(db: AsyncSession, user_id: int) -> List[Dict]:
    """
    Obtain data per category for charts
    """
    current_month_start = date.today().replace(day=1)

    category_data = await db.execute(
        select(
            Category.name.label('category'),
            func.sum(func.abs(Transaction.amount)).label('amount')
        )
        .join(Transaction, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.amount < 0,
                Transaction.transaction_date >= current_month_start,
            )
        )
        .group_by(Category.name)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
    )

    data = []
    for row in category_data:
        data.append({
            "category": row.category,
            "amount": round(float(row.amount or 0), 2)
        })

    return data


async def get_recent_transactions(db: AsyncSession, user_id: int, limit: int = 10) -> List[Dict]:
    """
    Obtain the most recent transactions with category information
    """
    recent_transactions = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(limit)
    )

    data = []
    for transaction in recent_transactions.scalars():
        data.append({
            "id": transaction.id,
            "description": transaction.description,
            "amount": round(float(transaction.amount), 2),
            "date": transaction.transaction_date.isoformat(),
            "category": transaction.category.name,
            "type": "income" if transaction.amount > 0 else "expense",
        })

    return data


async def get_budget_overview(db: AsyncSession, user_id: int) -> List[Dict]:
    """
    Obtain summary of budgets with current expenses
    """
    current_month_start = date.today().replace(day=1)
    current_month_end = date.today()

    budgets_query = await db.execute(
        select(Budget)
        .options(selectinload(Budget.category))
        .where(
            and_(
                Budget.user_id == user_id,
                Budget.start_date <= current_month_end,
                Budget.end_date >= current_month_start
            )
        )
    )

    data = []
    for budget in budgets_query.scalars():
        spent_query = await db.execute(
            select(func.sum(func.abs(Transaction.amount)))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.category_id == budget.category_id,
                    Transaction.amount < 0,
                    Transaction.transaction_date >= max(budget.start_date, current_month_start),
                    Transaction.transaction_date <= min(budget.end_date, current_month_end),
                )
            )
        )

        spent = float(spent_query.scalar() or 0)
        budget_amount = float(budget.amount)
        percentage = (spent / budget_amount) * 100 if budget_amount > 0 else 0
        if percentage > 100:
            status = "over"
        elif percentage >= 80:
            status = "warning"
        else:
            status = "good"

        data.append({
            "category": budget.category.name,
            "spent": round(spent, 2),
            "budget": round(budget_amount, 2),
            "percentage": round(percentage, 1),
            "remaining": round(max(budget_amount - spent, 0), 2),
            "status": status
        })

    return data
