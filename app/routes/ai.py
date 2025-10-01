from typing import Dict

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.services.ai_service import predict_future_transactions, get_ai_insights_data, generate_financial_insights, \
    analyze_spending_trends, generate_balance_forecast, generate_spending_predictions, generate_risk_analysis, \
    generate_smart_recommendations
from app.services.auth_service import get_current_user
from app.services.metrics_service import get_budget_overview, calculate_financial_summary

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
                "data": {
                    "insights": [
                        {
                            "type": "tip",
                            "title": "Empieza a registrar transacciones",
                            "message": "Registra tus gastos e ingresos para obtener análisis personalizados con IA",
                            "confidence": "Alta",
                            "icon": "lightbulb",
                            "color": "secondary"
                        }
                    ],
                    "message": "No hay suficientes transacciones para generar insights"
                },
                "user_id": current_user.id,
                "transactions_analyzed": 0
            }
        budget_data = await get_budget_overview(db, current_user.id)
        financial_summary = await calculate_financial_summary(db, current_user.id)

        ai_response = await generate_financial_insights(
            transactions=insights_data["transactions"],
            budgets=budget_data,
            financial_summary=financial_summary
        )
        if "error" in ai_response:
            return {
                "success": False,
                "error": "AI service unavailable",
                "data": {
                    "insights": [],
                    "message": "Los insights de IA no están disponibles temporalmente."
                },
                "user_id": current_user.id,
            }
        return {
            "success": True,
            "data": ai_response,
            "transactions_analyzed": len(insights_data["transactions"])
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "insights": [
                    {
                        "type": "warning",
                        "title": "Error generando insights",
                        "message": "Hubo un problema al generar los insights. Por favor, intenta más tarde.",
                        "confidence": "Alta",
                        "icon": "alert-triangle",
                        "color": "destructive"
                    }
                ]
            },
            "user_id": current_user.id
        }

@router.get("/spending-trends",
            summary="Analyze spending trends",
            description="Analyze user's spending trends over time to identify patterns and changes in financial behavior.",
            response_model=Dict)
async def get_spending_trends(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Analyzes user's spending trends.
    """
    try:
        insights_data = await get_ai_insights_data(db, current_user.id)

        if not insights_data["transactions"]:
            return {
                "success": True,
                "data": {
                    "trend":"neutral",
                    "message": "No hay suficientes transacciones para generar insights",
                    "percentage":0
                },
                "user_id": current_user.id,
            }

        trend_analysis = await analyze_spending_trends(insights_data["transactions"])

        return {
            "success": True,
            "data": trend_analysis,
            "user_id": current_user.id,
            "transactions_analyzed": len(insights_data["transactions"])
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "trend":"neutral",
                "message": "Error analizando tendencias",
                "percentage":0
            },
            "user_id": current_user.id
        }


@router.get("/predictions/spending",
            summary="Get spending predictions",
            description="Predict future spending patterns by category")
async def get_spending_predictions(
        timeframe: str = Query("1month", regex="^(1month|3months|6months)$"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get AI predictions for future spending by category
    """
    try:
        insights_data = await get_ai_insights_data(db, current_user.id)

        if not insights_data["transactions"]:
            return {
                "success": True,
                "predictions": [],
                "message": "No hay suficientes datos para predicciones"
            }

        predictions = await generate_spending_predictions(
            insights_data["transactions"],
            timeframe
        )

        return {
            "success": True,
            "predictions": predictions,
            "timeframe": timeframe
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "predictions": []
        }


@router.get("/forecast/balance",
            summary="Get balance forecast",
            description="Forecast future balance with optimistic, realistic, and conservative scenarios")
async def get_balance_forecast(
        timeframe: str = Query("6months", regex="^(3months|6months|1year)$"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get balance forecast for different scenarios
    """
    try:
        insights_data = await get_ai_insights_data(db, current_user.id)

        if not insights_data["transactions"]:
            return {
                "success": False,
                "forecast": None,
                "message": "No hay suficientes datos para pronóstico"
            }

        forecast = await generate_balance_forecast(
            insights_data["transactions"],
            timeframe
        )

        return {
            "success": True,
            "forecast": forecast
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "forecast": None
        }


@router.get("/recommendations",
            summary="Get smart recommendations",
            description="Get AI-powered personalized financial recommendations")
async def get_recommendations(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get personalized smart recommendations
    """
    try:
        insights_data = await get_ai_insights_data(db, current_user.id)
        budget_data = await get_budget_overview(db, current_user.id)
        financial_summary = await calculate_financial_summary(db, current_user.id)

        if not insights_data["transactions"]:
            return {
                "success": True,
                "recommendations": [],
                "message": "No hay suficientes datos para recomendaciones"
            }

        recommendations = await generate_smart_recommendations(
            insights_data["transactions"],
            budget_data,
            financial_summary
        )

        return {
            "success": True,
            "recommendations": recommendations
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "recommendations": []
        }


@router.post("/recommendations/{recommendation_id}/apply",
             summary="Apply a recommendation",
             description="Mark a recommendation as applied/actioned")
async def apply_recommendation(
    recommendation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Apply/action a specific recommendation (placeholder for future implementation)
    """
    # TODO: Implement logic to track applied recommendations
    # This could involve creating budgets, setting goals, etc.

    return {
        "success": True,
        "message": f"Recomendación {recommendation_id} aplicada correctamente",
        "recommendation_id": recommendation_id
    }


@router.get("/savings-goals/predictions",
            summary="Get savings goal predictions",
            description="Predict likelihood of achieving savings goals")
async def get_savings_goal_predictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Predict savings goals completion (placeholder for future implementation)
    """
    # TODO: Implement when savings goals model is ready

    return {
        "success": True,
        "predictions": [],
        "message": "Funcionalidad de metas de ahorro en desarrollo"
    }


@router.get("/risk-analysis",
            summary="Get financial risk analysis",
            description="Analyze financial health and risk factors")
async def get_risk_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive risk analysis
    """
    try:
        insights_data = await get_ai_insights_data(db, current_user.id)
        budget_data = await get_budget_overview(db, current_user.id)
        financial_summary = await calculate_financial_summary(db, current_user.id)

        if not insights_data["transactions"]:
            return {
                "success": False,
                "analysis": None,
                "message": "No hay suficientes datos para análisis de riesgo"
            }

        analysis = await generate_risk_analysis(
            insights_data["transactions"],
            budget_data,
            financial_summary
        )

        return {
            "success": True,
            "analysis": analysis
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "analysis": None
        }


@router.post("/refresh",
             summary="Refresh AI analysis",
             description="Force refresh of all AI-generated insights and predictions")
async def refresh_ai_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Refresh all AI analysis (triggers re-computation)
    """
    try:
        # Re-fetch all data to ensure fresh analysis
        insights_data = await get_ai_insights_data(db, current_user.id)

        if not insights_data["transactions"]:
            return {
                "success": False,
                "message": "No hay transacciones para analizar"
            }

        return {
            "success": True,
            "message": "Análisis actualizado correctamente",
            "timestamp": insights_data["transactions"][0]["date"] if insights_data["transactions"] else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error al actualizar análisis"
        }