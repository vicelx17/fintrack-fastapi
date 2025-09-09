from datetime import timezone, timedelta, date

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.report_schema import ReportResponse
from app.services.auth_service import get_current_user
from app.services.report_service import generate_report

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/", response_model=ReportResponse)
async def get_custom_report(
        start_date: date = Query(None, description="Start date"),
        end_date: date = Query(None, description="End date"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    report = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return report

@router.get("/weekly", response_model=ReportResponse)
async def get_weekly_report(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    weekly_report = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return weekly_report

@router.get("/monthly", response_model=ReportResponse)
async def get_monthly_report(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    monthly_report = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return monthly_report