
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.transaction import TransactionResponse, TransactionCreate, TransactionUpdate
from app.services.auth_service import get_current_user
from app.services.transaction_service import get_transactions, create_transaction, update_transaction, \
    delete_transaction

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("/", response_model=List[TransactionResponse])
async def list_user_transactions(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_transactions(db, current_user.id)

@router.post("/",
             response_model=TransactionResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new transaction",
             description="Allows the authenticated user to create a new transaction associated to an existing category",
             )
async def create_new_transaction(
        transaction: TransactionCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
        Example of **request body**:
        ```json
        {
          "amount": -30.0,
          "description": "Dinning in a restaurant",
          "category_id": 3
        }
        ```

        Example of **response**:
        ```json
        {
          "id": 101,
          "amount": -30.0,
          "description": "Dinning in a restaurant",
          "category_id": 3,
          "date": "2025-09-09"
        }
        ```
        """
    return await create_transaction(db, current_user.id, transaction)

@router.put("/{id}", response_model=TransactionResponse)
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

@router.delete("/{id}")
async def delete_user_transaction(
        id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await delete_transaction(db, current_user.id, id)
