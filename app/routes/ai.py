from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.services.ai_service import predict_future_transactions
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/ai", tags=["AI Predictions"])


@router.get("/predict")
async def predict_transaction(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Predict future transaction for the logged-in user using Gemini AI.
    """
    result = await db.execute(select(Transaction).where(Transaction.user_id == current_user.id))
    transactions = result.scalars().all()

    if not transactions:
        return {
            "user_id": current_user.id,
            "message": "No transactions found for prediction",
            "predictions": []
        }

    transactions_list = [
        {
            "id": t.id,
            "amount": float(t.amount),
            "description": t.description,
            "date": t.transaction_date.isoformat(),
            "category_id": t.category_id
        }
        for t in transactions
    ]

    ai_response = await predict_future_transactions(transactions_list)

    if "error" in ai_response:
        return {
            "user_id": current_user.id,
            "error": True,
            "details": ai_response
        }

    return {
        "user_id": current_user.id,
        "prediction": ai_response,
        "total_predictions": len(ai_response.get("predictions", []))
    }