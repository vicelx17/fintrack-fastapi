from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_db
from app.models.user import User
from app.services.ai_service import predict_future_transactions
from app.services.auth_service import get_current_user
from app.services.metrics_service import calculate_financial_summary, get_monthly_chart_data, get_category_chart_data, \
    get_recent_transactions, get_budget_overview, get_ai_insights_data

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/financial-summary",
            description="Returns main financial metrics for dashboard cards: balance, income, expenses, savings with month-over-month comparisons.",
            response_model=Dict)
async def get_financial_summary(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtains financial metrics for dashboard cards.
    """
    try:
        summary = await calculate_financial_summary(db, current_user.id)
        return {
            "sucess": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating financial metrics: {str(e)}"
        )

@router.get("/monthly-data",
            summary="Get monthly chart data",
            description="Returns income, expenses and balance data for the last 6 months for area/line charts.",
            response_model=Dict)
async def get_monthly_data(
        months: int = 6,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtains data for the monthly chart
    """
    try:
        if months < 1 or months > 24:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Months parameter must be between 1 and 24"
            )
        monthly_data = await get_monthly_chart_data(db, current_user.id, months)
        return {
            "success": True,
            "data": monthly_data,
            "period_month": months
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting monthly data: {str(e)}"
        )

@router.get("/category-data",
            summary="Get monthly expenses data",
            description="Returns current month expenses grouped by category for bar charts and category analysis.",
            response_model=Dict)
async def get_category_data(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtain expenses data per category for bar graphic chart.
    """
    try:
        category_data = await get_category_chart_data(db, current_user.id)
        return {
            "success": True,
            "data": category_data,
            "total_categories": len(category_data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting category data: {str(e)}"
        )

@router.get("/recent-transactions",
            summary="Get recent transactions",
            description="Returns the most recent transactions with category information for the dashboard transactions list.",
            response_model=Dict)
async def get_recent_transactions_endpoint(
        limit: int = 10,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtains most recent transactions for show them in the main dashboard.
    """
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit parameter must be between 1 and 50"
            )
        recent_data = await get_recent_transactions(db, current_user.id, limit)
        return {
            "success": True,
            "data": recent_data,
            "count": len(recent_data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recent transactions: {str(e)}"
        )

@router.get("/budget-overview",
            summary="Get budget overview",
            description="Returns current month budget status with spent amounts, percentages, and alerts for budget management.",
            response_model=Dict)
async def get_budget_overview_endpoint(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtain budget summary for the current month.
    """
    try:
        budget_data = await get_budget_overview(db, current_user.id)

        total_budgets = len(budget_data)
        over_budget = sum(1 for b in budget_data if b["status"] == "over")
        warning_budget = sum(1 for b in budget_data if b["status"] == "warning")

        return {
            "success": True,
            "data": budget_data,
            "stats": {
                "total_budgets": total_budgets,
                "over_budget_count": over_budget,
                "warning_budget_count": warning_budget,
                "good_budget_count": total_budgets - over_budget - warning_budget,
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting budget overview: {str(e)}"
        )

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

@router.get("/complete",
            summary="Get complete dsashboard data",
            description="Returns all dashboard data in a single request for initial page load optimization.",
            response_model=Dict)
async def get_complete_dashboard(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Optimized endpoint that returns all dashboard data in a single request.
    """
    try:
        financial_summary = await calculate_financial_summary(db, current_user.id)
        monthly_data = await get_monthly_chart_data(db, current_user.id, 6)
        category_data = await get_category_chart_data(db, current_user.id)
        recent_data = await get_recent_transactions(db, current_user.id, 10)
        budget_data = await get_budget_overview(db, current_user.id)

        return {
            "success": True,
            "data": {
                "financial_summary": financial_summary,
                "monthly_chart": monthly_data,
                "category_chart": category_data,
                "recent_transactions": recent_data,
                "budget_overview": budget_data
            },
            "user_id": current_user.id,
            "timestamp": "now"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting complete dashboard data: {str(e)}"
        )

@router.get("/health",
            summary="Dashboard health check",
            description="Simple health check endpoint to verify dashboard API is working.",
            response_model=Dict)
async def dashboard_health_check():
    """
    Health check for verify dashboard module is working.
    """
    return {
        "status": "healthy",
        "service": "dashboard",
    }

