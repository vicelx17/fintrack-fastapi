from datetime import timedelta, date

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse, JSONResponse

from app.core.database import get_db
from app.models.user import User
from app.schemas.report_schema import ReportResponse
from app.services.auth_service import get_current_user
from app.services.report_service import generate_report, generate_pdf_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/custom", summary="Generate Custom Report",
            description="Generate a financial report for a custom date range", response_model=ReportResponse)
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


@router.get("/weekly", summary="Generate Weekly Report",
            description="Generate a financial report for the last 7 days", response_model=ReportResponse)
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


@router.get("/monthly", summary="Generate Monthly Report",
            description="Generate a financial report for the last 30 days", response_model=ReportResponse)
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


@router.get("/generate/pdf",
            summary="Export Report as PDF",
            description="Generate and download a complete financial report as PDF"
            )
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


@router.get("/generate/custom_pdf",
            summary="Export PDF report with custom date ranges",
            description="Generate and download a complete financial report as PDF")
async def export_custom_pdf_report(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        start_date: date = Query(None, description="Start date"),
        end_date: date = Query(None, description="End date")
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    report_data = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    pdf_file = await generate_pdf_report(report_data)
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=financial_weekly_report.pdf"
        }
    )


@router.get("/generate/weekly_pdf",
            summary="Export Weekly PDF report with last 7 days",
            description="Generate and download a complete financial report in PDF format for the last 7 days")
async def export_weekly_pdf(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
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
            "Content-Disposition": "attachment; filename=financial_weekly_report.pdf"
        }
    )


@router.get("/generate/monthly_pdf",
            summary="Export Monthly PDF report with last 30 days",
            description="Generate and download a complete financial report in PDF format for the last 30 days")
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


@router.get("/generate/json",
            summary="Generate JSON Report",
            description="Generate report as JSON", )
async def export_json_report(
        db: AsyncSession = Depends(get_db),
        start_date: date = None,
        end_date: date = None,
        current_user: User = Depends(get_current_user)
):
    report_data = await generate_report(
        db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )

    data = report_data.model_dump(mode="json")

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=report_{current_user.username}.json"
        }
    )


@router.get("/generate/custom_json",
            summary="Generate JSON Report with custom date ranges",
            description="Generate report as JSON")
async def export_custom_json_report(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        start_date: date = Query(None, description="Start date"),
        end_date: date = Query(None, description="End date")
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    report_data = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    data = report_data.model_dump(mode="json")
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=custom_report_{current_user.username}.json"
        }
    )


@router.get("/generate/weekly_json",
            summary="Generate weekly JSON Report",
            description="Generate report as JSON format for the last 7 days.")
async def export_weekly_json_report(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        end_date: date = date.today(),
        start_date: date = date.today() - timedelta(days=7)
):
    report_data = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    data = report_data.model_dump(mode="json")
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=custom_report_{current_user.username}.json"
        }
    )


@router.get("/generate/monthly_json",
            summary="Generate monthly JSON Report",
            description="Generate report as JSON format for the last 30 days.")
async def export_monthly_json_report(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        end_date: date = date.today(),
        start_date: date = date.today() - timedelta(days=30)
):
    report_data = await generate_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    data = report_data.model_dump(mode="json")
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=custom_report_{current_user.username}.json"
        }
    )