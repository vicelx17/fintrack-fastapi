from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.services.ai_service import predict_future_transactions, get_ai_insights_data
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

@router.get("/ai-insights",
            summary="Get AI-powered financial insights",
            description="Returns AI-generated insights and predictions based on user's transaction history and spending patterns.",
            response_model=Dict)
async def get_ai_insights_endpoint(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtain AI-insights data based in transaction patterns.
    """
    try:
        insights_data = await get_ai_insights_data(db, current_user.id)
        if not insights_data["transactions"]:
            return {
                "success": True,
                "data":{
                    "insights": [],
                    "message": "No hay suficientes transacciones para generar insights"
                }
            }

        ai_response = await predict_future_transactions(insights_data["transactions"])
        if "error" in ai_response:
            return {
                "success": False,
                "error": "AI service unavailable",
                "data": {
                    "insights": [],
                    "message": "Los insights de IA no están disponibles temporalmente."
                }
            }
        return {
            "success": True,
            "data": {
                "insights": ai_response.get("predictions", []),
                "user_id": current_user.id,
                "analysis_date": insights_data.get("analysis_date"),
                "transactions_analyzed": len(insights_data["transactions"]),
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting AI-insights: {str(e)}"
        )