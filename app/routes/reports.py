from datetime import timedelta, date

from fastapi import APIRouter, Query, Depends, HTTPException
from fontTools.misc.plistlib import end_date
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.database import get_db
from app.models.user import User
from app.schemas.report_schema import ReportResponse
from app.services.auth_service import get_current_user
from app.services.report_service import generate_report, generate_pdf_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/custom", response_model=ReportResponse)
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


@router.get("/generate/pdf")
async def export_report_pdf(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    report_data = await generate_report(db, current_user.id)
    pdf_file = await generate_pdf_report(report_data)
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=financial_report.pdf"
        }
    )


@router.get("/generate/custom_pdf")
async def get_custom_report(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        start_date: date = Query(None, description="Start date"),
        end_date: date = Query(None, description="End date")
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    custom_report_data = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    pdf_file = await generate_pdf_report(custom_report_data)
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=financial_weekly_report.pdf"
        }
    )


@router.get("/generate/weekly_pdf")
async def export_weekly_pdf(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    report_weekly_data = await generate_report(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    pdf_file = await generate_pdf_report(report_weekly_data)
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=financial_weekly_report.pdf"
        }
    )


@router.get("/generate/monthly_pdf")
async def export_monthly_pdf(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    report_data = await generate_report(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    pdf_file = await generate_pdf_report(report_data)
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=financial_monthly_report.pdf"
        }
    )
