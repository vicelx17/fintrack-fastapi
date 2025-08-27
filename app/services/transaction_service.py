from datetime import datetime, timezone

from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.Transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate


async def create_transaction(db: AsyncSession, user_id: int, transaction: TransactionCreate):
    new_transaction = Transaction(
        user_id=user_id,
        amount=transaction.amount,
        description=transaction.description,
        category_id=transaction.category_id,
        date=datetime.now(timezone.utc),
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    return new_transaction

async def get_transactions(db: AsyncSession, user_id: int) -> Transaction:
    result = await db.execute(select(Transaction).where(Transaction.user_id == user_id))
    return result.scalars().all()

async def update_transaction(db: AsyncSession, user_id: int, transaction_id: int, transaction_update: TransactionUpdate):
    query = (
        update(Transaction)
        .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
        .values(transaction_update.model_dump(exclude_unset=True))
        .returning(Transaction)
    )
    result = await db.execute(query)
    await db.commit()
    return result.scalars().one_or_none()

async def delete_transaction(db: AsyncSession, user_id: int, transaction_id: int):
    query = delete(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    await db.execute(query)
    await db.commit()
    return {"message": "Transaction deleted"}