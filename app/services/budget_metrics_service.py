# app/services/budget_metrics_service.py
from typing import Dict, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction


async def get_budget_alerts(db: AsyncSession, user_id: int) -> List[Dict]:
    """
    Generate alerts for budgets that are approaching or exceeding their limits.
    """
    alerts = []

    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id)
    )
    budgets = result.scalars().all()

    for budget in budgets:
        spent_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_date >= budget.start_date,
                Transaction.transaction_date <= budget.end_date,
                Transaction.type == "expense"
            )
        )
        spent_amount = spent_result.scalar() or 0.0

        category_result = await db.execute(
            select(Category).where(Category.id == budget.category_id)
        )
        category = category_result.scalar_one_or_none()
        category_name = category.name if category else "Unknown"

        percentage = (spent_amount / budget.amount) * 100 if budget.amount > 0 else 0

        if spent_amount > budget.amount:
            overage = spent_amount - budget.amount
            alerts.append({
                "id": f"alert-{budget.id}-exceeded",
                "budgetId": budget.id,
                "type": "exceeded",
                "category": category_name,
                "message": f"Has excedido el presupuesto en €{overage:.2f}",
                "severity": "high",
                "dismissed": False,
            })
        elif percentage >= budget.alert_threshold:
            alerts.append({
                "id": f"alert-{budget.id}-warning",
                "budgetId": budget.id,
                "type": "warning",
                "category": category_name,
                "message": f"Has usado el {percentage:.0f}% de tu presupuesto (€{spent_amount:.0f} de €{budget.amount:.0f})",
                "severity": "medium" if percentage >= 90 else "low",
                "dismissed": False,
            })

    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda x: severity_order.get(x["severity"], 3))

    return alerts

async def get_budget_overview(db: AsyncSession, user_id: int) -> Dict:
    """
    Calculate overall budget metrics for the user.
    """
    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id)
    )
    budgets = result.scalars().all()

    total_budget = 0.0
    total_spent = 0.0
    budgets_exceeded = 0
    total_budgets = len(budgets)

    for budget in budgets:
        total_budget += budget.amount

        spent_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_date >= budget.start_date,
                Transaction.transaction_date <= budget.end_date,
                Transaction.type == "expense"
            )
        )
        spent_amount = spent_result.scalar() or 0.0
        total_spent += spent_amount

        if spent_amount > budget.amount:
            budgets_exceeded += 1

    available = total_budget - total_spent
    percentage_used = (total_spent / total_budget * 100) if total_budget > 0 else 0

    return {
        "totalBudget": total_budget,
        "totalSpent": total_spent,
        "available": available,
        "percentageUsed": percentage_used,
        "budgetsExceeded": budgets_exceeded,
        "totalBudgets": total_budgets,
    }


async def get_category_spending_breakdown(db: AsyncSession, user_id: int, start_date: date = None,
                                          end_date: date = None) -> List[Dict]:
    """
    Get spending breakdown by category for a given period.
    """
    if not start_date or not end_date:
        today = date.today()
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year, 12, 31)
        else:
            end_date = date(today.year, today.month + 1, 1)

    # Expenses by category
    result = await db.execute(
        select(
            Category.id,
            Category.name,
            func.sum(Transaction.amount).label("total_spent"),
            func.count(Transaction.id).label("transaction_count")
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    )

    breakdown = []
    for row in result:
        budget_result = await db.execute(
            select(Budget)
            .where(
                Budget.user_id == user_id,
                Budget.category_id == row.id,
                Budget.start_date <= end_date,
                Budget.end_date >= start_date
            )
        )
        budget = budget_result.scalar_one_or_none()

        breakdown.append({
            "categoryId": row.id,
            "categoryName": row.name,
            "totalSpent": float(row.total_spent),
            "transactionCount": row.transaction_count,
            "budgetAmount": budget.amount if budget else None,
            "percentageOfBudget": (
                        float(row.total_spent) / budget.amount * 100) if budget and budget.amount > 0 else None,
        })

    return breakdown

async def get_budget_analytics(db: AsyncSession, user_id: int, period: str = "monthly") -> Dict:
    """
    Get comprehensive budget analytics for different time periods.
    """
    today = date.today()
    if period == "weekly":
        from datetime import timedelta
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == "monthly":
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year, 12, 31)
        else:
            end_date = date(today.year, today.month + 1, 1)
    elif period == "quarterly":
        quarter = (today.month - 1) // 3
        start_date = date(today.year, quarter * 3 + 1, 1)
        if quarter == 3:
            end_date = date(today.year, 12, 31)
        else:
            end_date = date(today.year, (quarter + 1) * 3 + 1, 1)
    elif period == "yearly":
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
    else:
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year, 12, 31)
        else:
            end_date = date(today.year, today.month + 1, 1)

    overview = await get_budget_overview(db, user_id)

    category_breakdown = await get_category_spending_breakdown(db, user_id, start_date, end_date)

    alerts = await get_budget_alerts(db, user_id)

    return {
        "period": period,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "overview": overview,
        "categoryBreakdown": category_breakdown,
        "alerts": alerts,
        "trends": {
            "spendingTrend": "stable",
            "savingsRate": ((overview["totalBudget"] - overview["totalSpent"]) / overview["totalBudget"] * 100) if
            overview["totalBudget"] > 0 else 0,
        }
    }

async def get_budget_performance(db: AsyncSession, user_id: int) -> List[Dict]:
    """
    Get performance metrics for each budget (% used, days remaining, etc.)
    """
    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id)
    )
    budgets = result.scalars().all()

    performance = []
    today = date.today()

    for budget in budgets:
        spent_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_date >= budget.start_date,
                Transaction.transaction_date <= budget.end_date,
                Transaction.type == "expense"
            )
        )
        spent_amount = spent_result.scalar() or 0.0

        category_result = await db.execute(
            select(Category).where(Category.id == budget.category_id)
        )
        category = category_result.scalar_one_or_none()

        # Metrics
        percentage_used = (spent_amount / budget.amount * 100) if budget.amount > 0 else 0
        days_total = (budget.end_date - budget.start_date).days + 1
        days_elapsed = (today - budget.start_date).days + 1
        days_remaining = (budget.end_date - today).days

        expected_spending = (days_elapsed / days_total * budget.amount) if days_total > 0 else 0
        spending_pace = "on_track"
        if spent_amount > expected_spending * 1.1:
            spending_pace = "over_pace"
        elif spent_amount < expected_spending * 0.9:
            spending_pace = "under_pace"

        performance.append({
            "budgetId": budget.id,
            "categoryName": category.name if category else "Unknown",
            "budgetAmount": budget.amount,
            "spentAmount": spent_amount,
            "percentageUsed": percentage_used,
            "daysRemaining": max(0, days_remaining),
            "daysTotal": days_total,
            "expectedSpending": expected_spending,
            "spendingPace": spending_pace,
            "isActive": budget.start_date <= today <= budget.end_date,
        })

    return performance