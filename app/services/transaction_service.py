from datetime import date, timedelta
from typing import Dict, Optional, List

from sqlalchemy import update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate

async def create_transaction(db: AsyncSession, user_id: int, transaction: TransactionCreate) -> Dict:
    new_transaction = Transaction(
        user_id=user_id,
        amount=transaction.amount,
        description=transaction.description,
        category_id=transaction.category_id,
        transaction_date=transaction.transaction_date or date.today(),
        notes=transaction.notes,
        type=transaction.type,
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    category_result = await db.execute(
        select(Category).where(Category.id == new_transaction.category_id)
    )
    category = category_result.scalar_one_or_none()
    return {
        "id": new_transaction.id,
        "userId": new_transaction.user_id,
        "type": new_transaction.type,
        "amount": new_transaction.amount,
        "description": new_transaction.description,
        "category": category.name,
        "transactionDate": new_transaction.transaction_date.isoformat(),
        "notes": new_transaction.notes,
        "createdAt": new_transaction.created_at.isoformat(),
        "updatedAt": new_transaction.updated_at.isoformat()
    }

async def get_transactions(db: AsyncSession,
                           user_id: int,
                           search: Optional[str] = None,
                           category: Optional[str] = None,
                           transaction_type: Optional[str] = None,
                           date_range: Optional[str] = None,
                           min_amount: Optional[float] = None,
                           max_amount: Optional[float] = None) -> List[Dict]:
    query = (
        select(Transaction, Category.name)
        .join(Category, Transaction.category_id == Category.id)
        .where(Transaction.user_id == user_id)
    )

    if search:
        query = query.where(Transaction.description.ilike(f"%{search}%"))
    if category:
        query = query.where(Category.name == category)
    if transaction_type:
        query = query.where(Transaction.type == transaction_type)
    if min_amount is not None:
        query = query.where(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.where(Transaction.amount <= max_amount)

    if date_range:
        today = date.today()

        if date_range == "today":
            query = query.where(Transaction.transaction_date == today)
        elif date_range == "week":
            week_ago = today - timedelta(days=7)
            query = query.where(Transaction.transaction_date >= week_ago)
        elif date_range == "month":
            month_ago = today - timedelta(days=30)
            query = query.where(Transaction.transaction_date >= month_ago)
        elif date_range == "quarter":
            quarter_ago = today - timedelta(days=90)
            query = query.where(Transaction.transaction_date >= quarter_ago)
        elif date_range == "year":
            year_ago = today - timedelta(days=365)
            query = query.where(Transaction.transaction_date >= year_ago)

    query = query.order_by(Transaction.transaction_date.desc())

    result = await db.execute(query)
    transactions = result.all()

    return [
        {
            "id": str(transaction.id),
            "userId": str(transaction.user_id),
            "type": transaction.type,
            "amount": transaction.amount,
            "description": transaction.description,
            "category": category_name,
            "transactionDate": transaction.transaction_date.isoformat(),
            "notes": transaction.notes,
            "createdAt": transaction.created_at.isoformat() if transaction.created_at else None,
            "updatedAt": transaction.updated_at.isoformat() if transaction.updated_at else None,
        }
        for transaction, category_name in transactions
    ]

async def get_transaction_by_id(db: AsyncSession, user_id: int, transaction_id: int) -> Optional[Dict]:
    """Get a specific transaction by id"""
    result = await db.execute(
        select(Transaction, Category.name)
        .join(Category, Transaction.category_id == Category.id)
        .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )

    row = result.first()
    if not row:
        return None

    transaction, category_name = row
    return {
        "id": str(transaction.id),
        "userId": str(transaction.user_id),
        "type": transaction.type,
        "amount": transaction.amount,
        "description": transaction.description,
        "category": category_name,
        "transactionDate": transaction.transaction_date.isoformat(),
        "notes": transaction.notes,
        "createdAt": transaction.created_at.isoformat() if transaction.created_at else None,
        "updatedAt": transaction.updated_at.isoformat() if transaction.updated_at else None
    }


async def get_transaction_stats(db: AsyncSession, user_id: int, date_range: Optional[str] = None) -> Dict:
    """Get transaction statistics"""
    query = select(Transaction).where(Transaction.user_id == user_id)

    today = date.today()
    start_date = None
    days_count = 30

    if date_range:
        if date_range == "today":
            start_date = today
            days_count = 1
        elif date_range == "week":
            start_date = today - timedelta(days=7)
            days_count = 7
        elif date_range == "month":
            start_date = today - timedelta(days=30)
            days_count = 30
        elif date_range == "quarter":
            start_date = today - timedelta(days=90)
            days_count = 90
        elif date_range == "year":
            start_date = today - timedelta(days=365)
            days_count = 365
    else:
        start_date = today - timedelta(days=30)
        days_count = 30

    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)

    result = await db.execute(query)
    transactions = result.scalars().all()

    total_transactions = len(transactions)
    total_income = sum(abs(transaction.amount) for transaction in transactions if transaction.type == "income")
    total_expenses = sum(abs(transaction.amount) for transaction in transactions if transaction.type == "expense")

    # Balance neto = ingresos - gastos
    net_balance = total_income - total_expenses

    # Promedio diario del balance neto
    average_daily = (net_balance / days_count) if days_count > 0 else 0

    return {
        "totalTransactions": total_transactions,
        "totalIncome": round(total_income, 2),
        "totalExpenses": round(total_expenses, 2),
        "averageDaily": round(average_daily, 2),
    }

async def get_category_breakdown(db: AsyncSession, user_id: int, date_range: Optional[str] = None) -> List[Dict]:
    query = (
        select(
            Category.name,
            Transaction.type,
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .join(Transaction, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user_id)
    )

    if date_range:
        today = date.today()
        start_date = None

        if date_range == "today":
            start_date = today
        elif date_range == "week":
            start_date = today - timedelta(days=7)
        elif date_range == "month":
            start_date = today - timedelta(days=30)
        elif date_range == "quarter":
            start_date = today - timedelta(days=90)
        elif date_range == "year":
            start_date = today - timedelta(days=365)

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)

    query = query.group_by(Category.name, Transaction.type).order_by(func.sum(func.abs(Transaction.amount)).desc())

    result = await db.execute(query)
    breakdown = result.all()

    return [
        {
            "category": name,
            "type": type,
            "amount": round(float(total), 2)
        }
        for name, type, total in breakdown
    ]

async def update_transaction(db: AsyncSession, user_id: int, transaction_id: int,
                             transaction_update: TransactionUpdate) -> Optional[Dict]:
    query = (
        update(Transaction)
        .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
        .values(transaction_update.model_dump(exclude_unset=True))
        .returning(Transaction)
    )
    result = await db.execute(query)
    await db.commit()
    updated_transaction = result.scalars().one_or_none()
    if not updated_transaction:
        return None

    category_result = await db.execute(
        select(Category).where(Category.id == updated_transaction.category_id)
    )
    category = category_result.scalar_one_or_none()

    return {
        "id": str(updated_transaction.id),
        "userId": str(updated_transaction.user_id),
        "type": updated_transaction.type,
        "amount": updated_transaction.amount,
        "description": updated_transaction.description,
        "category": category.name,
        "transactionDate": updated_transaction.transaction_date.isoformat(),
        "notes": updated_transaction.notes,
        "createdAt": updated_transaction.created_at.isoformat() if updated_transaction.created_at else None,
        "updatedAt": updated_transaction.updated_at.isoformat() if updated_transaction.updated_at else None,
    }

async def delete_transaction(db: AsyncSession, user_id: int, transaction_id: int) -> Dict:
    query = delete(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    result = await db.execute(query)
    await db.commit()

    if result.rowcount == 0:
        return {"success": False, "message": "Transaction not found"}

    return {"success": True, "message": "Transaction deleted"}