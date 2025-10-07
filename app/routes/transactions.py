from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.auth_service import get_current_user
from app.services.transaction_service import (
    get_transactions,
    create_transaction,
    update_transaction,
    delete_transaction,
    get_transaction_by_id,
    get_transaction_stats,
    get_category_breakdown
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/",
            response_model=List[Dict],
            summary="Get all user transactions",
            description="Allows the user to get all of their transactions",
            )
async def list_user_transactions(
        search: Optional[str] = Query(None, description="Search in description"),
        category: Optional[str] = Query(None, description="Filter by category"),
        type: Optional[str] = Query(None, description="Filter by type (income/expense)"),
        dateRange: Optional[str] = Query(None, description="Filter by date range"),
        minAmount: Optional[str] = Query(None, description="Filter by minimum amount"),
        maxAmount: Optional[str] = Query(None, description="Filter by maximum amount"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await get_transactions(
        db,
        current_user.id,
        search=search,
        category=category,
        transaction_type=type,
        date_range=dateRange,
        min_amount=minAmount,
        max_amount=maxAmount
    )


@router.get("/stats",
            response_model=Dict,
            summary="Get transaction statistics",
            description="Get statistics about user transactions",
            )
async def get_user_transaction_stats(
        dateRange: Optional[str] = Query(None, description="Filter by date range"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await get_transaction_stats(db, current_user.id, dateRange)


@router.get("/category-breakdown",
            response_model=List[Dict],
            summary="Get category breakdown",
            description="Get breakdown of transactions by category",
            )
async def get_user_category_breakdown(
        dateRange: Optional[str] = Query(None, description="Filter by date range"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await get_category_breakdown(db, current_user.id, dateRange)


@router.get("/{id}",
            response_model=Dict,
            summary="Get transaction by id",
            description="Allows the user to get a transaction by id",
            )
async def get_user_transaction(
        id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    transaction = await get_transaction_by_id(db, current_user.id, id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return transaction


@router.post("/",
             response_model=Dict,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new transaction",
             description="Allows the authenticated user to create a new transaction associated to an existing category",
             )
async def create_new_transaction(
        transaction: TransactionCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await create_transaction(db, current_user.id, transaction)


@router.put("/{id}",
            response_model=Dict,
            summary="Update an existing transaction",
            description="Allows the authenticated user to update an existing transaction", )
async def update_user_transaction(
        id: int,
        transaction: TransactionUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    tx = await update_transaction(db, current_user.id, id, transaction)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return tx


@router.delete("/{id}",
               response_model=Dict,
               summary="Delete an existing transaction",
               description="Allows the authenticated user to delete an existing transaction", )
async def delete_user_transaction(
        id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await delete_transaction(db, current_user.id, id)