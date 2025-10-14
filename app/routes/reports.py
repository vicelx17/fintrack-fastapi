from typing import Dict

from app.services.budget_metrics_service import get_category_spending_breakdown
from app.services.metrics_service import get_monthly_chart_data
from datetime import timedelta, date

from fastapi import APIRouter, Query, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse, JSONResponse

from app.core.database import get_db
from app.models.user import User
from app.schemas.report_schema import ReportResponse
from app.services.auth_service import get_current_user
from app.services.report_service import generate_report, generate_pdf_report, export_report_by_filters, \
    get_trend_analysis_by_period, get_income_analysis_by_period, get_expense_analysis_by_period, \
    get_financial_summary_by_period

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


@router.get("/summary",
            summary="Get financial summary for period",
            description="Returns financial summary metrics for a specific period")
async def get_financial_summary_report(
        period: str = Query("month", description="Period: week, month, quarter, year"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get financial summary for a specific period."""
    try:
        summary = await get_financial_summary_by_period(db, current_user.id, period)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting financial summary: {str(e)}")


@router.get("/expenses",
            summary="Get expense analysis by category",
            description="Returns detailed expense analysis for a period")
async def get_expense_analysis(
        period: str = Query("month", description="Period: week, month, quarter, year"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get expense analysis by category for a period."""
    try:
        analysis = await get_expense_analysis_by_period(db, current_user.id, period)
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting expense analysis: {str(e)}")


@router.get("/income",
            summary="Get income analysis by category",
            description="Returns detailed income analysis for a period")
async def get_income_analysis(
        period: str = Query("month", description="Period: week, month, quarter, year"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get income analysis by category for a period."""
    try:
        analysis = await get_income_analysis_by_period(db, current_user.id, period)
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting income analysis: {str(e)}")


@router.get("/trends",
            summary="Get trend analysis",
            description="Returns trend data for income, expenses and balance")
async def get_trend_analysis(
        period: str = Query("month", description="Period: week, month, quarter, year"),
        granularity: str = Query("monthly", description="Granularity: daily, weekly, monthly"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get trend analysis for specified period and granularity."""
    try:
        trends = await get_trend_analysis_by_period(db, current_user.id, period)
        return {"trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trend analysis: {str(e)}")



@router.post("/export",
             summary="Export report in different formats",
             description="Export report as PDF, CSV or JSON based on filters")
async def export_report_endpoint(
        filters: Dict = Body(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Export report based on filters and format."""
    try:
        format_type = filters.get('format', 'pdf')

        if format_type not in ['pdf', 'json', 'csv']:
            raise HTTPException(status_code=400, detail="Format must be pdf, json or csv")

        print(f"Received filters: {filters}")
        print(f"Format: {format_type}")

        report_data, filename = await export_report_by_filters(
            db,
            current_user.id,
            filters,
            format_type
        )

        if format_type == 'pdf':
            return StreamingResponse(
                report_data,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        elif format_type == 'json':
            # Si es en JSON, devolver directamente datos
            return JSONResponse(
                content=report_data,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise HTTPException(status_code=400, detail="Format not yet implemented")

    except ValueError as e:
        print(f"ValueError in export: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Exception in export: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error exporting report: {str(e)}")


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
