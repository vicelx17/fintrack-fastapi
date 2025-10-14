from datetime import date, timedelta
from io import BytesIO
from typing import Dict, List, Optional

from matplotlib import pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction
from app.schemas.report_schema import ReportResponse, ReportTransaction, ReportCategory
from app.services.budget_metrics_service import get_category_spending_breakdown
from app.services.metrics_service import get_category_chart_data


async def generate_report(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None) -> ReportResponse:

    query = select(Transaction).options(selectinload(Transaction.category)).where(Transaction.user_id == user_id)

    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.where(Transaction.transaction_date <= end_date)

    result = await db.execute(query)
    transactions_data = result.scalars().all()

    if not transactions_data:
        return ReportResponse(
            total_income=0.0,
            total_expenses=0.0,
            net_balance=0.0,
            top_categories=[],
            transactions=[]
        )

    total_income = sum(t.amount for t in transactions_data if t.amount > 0)
    total_expenses = sum(abs(t.amount) for t in transactions_data if t.amount < 0)
    net_balance = total_income - total_expenses

    category_totals = {}

    for transaction in transactions_data:
        category_name = transaction.category.name if transaction.category else "Sin categoría"
        category_totals[category_name] = category_totals.get(category_name, 0) + transaction.amount

    top_categories = sorted(
        [ReportCategory(category=name, net_category_balance=balance) for name, balance in category_totals.items()],
        key=lambda c: c.net_category_balance    ,
        reverse=True
    )[:5]

    transactions_list = [
        ReportTransaction(
            id=transaction.id,
            amount=transaction.amount,
            description=transaction.description,
            report_date=transaction.transaction_date,
            category=transaction.category.name if transaction.category else "Sin categoría",
        )
        for transaction in transactions_data
    ]

    # Final response
    return ReportResponse(
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        top_categories=top_categories,
        transactions=transactions_list
    )


async def generate_pdf_report(report_data: ReportResponse) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    elements = []

    # ---- Header ----
    title_style = styles["Title"]
    title = Paragraph("FinTrack - Financial Report", title_style)
    elements.append(title)

    current_date = date.today().strftime("%Y-%m-%d")
    elements.append(Paragraph(f"Generated on: {current_date}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    # ---- Summary Section ----
    summary_data = [
        ["Metric", "Value"],
        ["Total Income", f"${report_data.total_income:.2f}"],
        ["Total Expenses", f"${report_data.total_expenses:.2f}"],
        ["Net Balance", f"${report_data.net_balance:.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                # HEADER - Verde oscuro profesional
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),

                # DATOS - Verde muy claro
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f7f1")),

                # BORDES - Verde suave
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#2d5a3d")),

                # PADDING AJUSTADO
                ("TOPPADDING", (0, 0), (-1, 0), 8),  # Header
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),  # Header
                ("TOPPADDING", (0, 1), (-1, -1), 6),  # Datos
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),  # Datos
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(Paragraph("Summary", styles["Heading2"]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ---- Generar gráfico si hay datos ----
    if report_data.top_categories:
        try:
            # Convertir los objetos ReportCategory a datos para el gráfico
            chart_categories = []
            for cat in report_data.top_categories:
                chart_categories.append({
                    "category": cat.category,
                    "total": float(cat.net_category_balance)
                })

            # Generar gráfico con matplotlib
            buffer_chart = BytesIO()

            categories = [cat["category"] for cat in chart_categories]
            totals = [cat["total"] for cat in chart_categories]

            plt.figure(figsize=(8, 5))
            # COLORES VERDES PARA EL GRÁFICO
            bars = plt.bar(categories, totals, color="#2d5a3d", edgecolor="#1a472a", linewidth=1.5)

            # Agregar valores encima de las barras
            for bar, total in zip(bars, totals):
                plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(totals) * 0.01,
                         f'${total:.2f}', ha='center', va='bottom', fontsize=10, color="#1a472a", fontweight='bold')

            plt.title("Top Categories - Net Balance", fontsize=14, fontweight="bold", color="#1a472a")
            plt.xlabel("Categories", fontsize=12, color="#2d5a3d")
            plt.ylabel("Net Balance ($)", fontsize=12, color="#2d5a3d")
            plt.xticks(rotation=45, ha="right", color="#2d5a3d")
            plt.yticks(color="#2d5a3d")
            plt.tight_layout()

            # Guardar en buffer
            plt.savefig(buffer_chart, format="png", dpi=100, bbox_inches='tight')
            plt.close()  # Cerrar para liberar memoria

            # Resetear posición del buffer
            buffer_chart.seek(0)

            # Crear imagen para el PDF
            chart_image = Image(buffer_chart, width=5 * inch, height=3 * inch)
            elements.append(Paragraph("Top Categories (Chart)", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))  # Consistente con el resto
            elements.append(chart_image)
            elements.append(Spacer(1, 0.3 * inch))

        except Exception as e:
            # Si hay error con el gráfico, solo mostrar un mensaje
            print(f"Error generando gráfico: {e}")
            elements.append(Paragraph("Top Categories (Chart unavailable)", styles["Heading2"]))
            elements.append(Spacer(1, 0.2 * inch))

    # ---- Top Categories Table ----
    elements.append(Paragraph("Top Categories (Table)", styles["Heading2"]))

    if report_data.top_categories:
        top_categories_data = [["Category", "Net Balance"]]
        for cat in report_data.top_categories:
            top_categories_data.append([cat.category, f"${cat.net_category_balance:.2f}"])
    else:
        top_categories_data = [["Category", "Net Balance"], ["No data available", "$0.00"]]

    top_categories_table = Table(top_categories_data, colWidths=[3 * inch, 3 * inch])
    top_categories_table.setStyle(
        TableStyle(
            [
                # HEADER - Verde oscuro profesional
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),

                # DATOS - Verde muy claro
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f7f1")),

                # BORDES - Verde suave
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#2d5a3d")),

                # PADDING COMPACTO
                ("TOPPADDING", (0, 0), (-1, 0), 8),  # Header
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),  # Header
                ("TOPPADDING", (0, 1), (-1, -1), 5),  # Datos más compactos
                ("BOTTOMPADDING", (0, 1), (-1, -1), 5),  # Datos más compactos
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(top_categories_table)
    elements.append(Spacer(1, 0.15 * inch))

    # ---- Transactions Section ----
    elements.append(Paragraph("Recent Transactions", styles["Heading2"]))
    elements.append(Spacer(1, 0.05 * inch))

    if report_data.transactions:
        transactions_data = [["Date", "Description", "Amount", "Category"]]
        for tx in report_data.transactions:
            transactions_data.append(
                [str(tx.report_date), tx.description,
                 f"${tx.amount:.2f}", tx.category]
            )
    else:
        transactions_data = [["Date", "Description", "Amount", "Category"],
                             ["No transactions", "available", "$0.00", "N/A"]]

    transactions_table = Table(
        transactions_data,
        colWidths=[1.5 * inch, 2.5 * inch, 1 * inch, 1.5 * inch]
    )


    transactions_table.setStyle(
        TableStyle(
            [
                # HEADER - Verde oscuro profesional
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),

                # DATOS - Verde muy claro alternando con blanco
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fdf9"), colors.white]),

                # BORDES - Verde suave
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2d5a3d")),

                # PADDING MUY COMPACTO - ESTO ELIMINA EL ESPACIO GRANDE
                ("TOPPADDING", (0, 0), (-1, 0), 6),  # Header normal
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),  # Header normal
                ("TOPPADDING", (0, 1), (-1, -1), 2),  # Datos MUY compactos
                ("BOTTOMPADDING", (0, 1), (-1, -1), 2),  # Datos MUY compactos
                ("LEFTPADDING", (0, 0), (-1, -1), 4),  # Menos padding horizontal también
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),  # Menos padding horizontal también
            ]
        )
    )

    elements.append(transactions_table)

    # ---- Footer ----
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph(
            "© 2025 FinTrack - Personal Finance Management Tool",
            styles["Normal"]
        )
    )

    # Construir el PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

async def get_financial_summary_by_period(
        db: AsyncSession,
        user_id: int,
        period: str
) -> Dict:
    """
    Get financial summary for a specific period.
    """
    from sqlalchemy import select, func, and_
    from app.models.transaction import Transaction

    end_date = date.today()

    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    # Calculate total income
    income_result = await db.execute(
        select(func.sum(Transaction.amount))
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == "income",
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
    )
    total_income = float(income_result.scalar() or 0)

    # Calculate total expenses
    expenses_result = await db.execute(
        select(func.sum(func.abs(Transaction.amount)))
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
    )
    total_expenses = float(expenses_result.scalar() or 0)

    # Calculate metrics
    net_balance = total_income - total_expenses
    savings_rate = (net_balance / total_income * 100) if total_income > 0 else 0
    days_count = (end_date - start_date).days + 1
    avg_daily_spending = total_expenses / days_count if days_count > 0 else 0

    return {
        "totalIncome": round(total_income, 2),
        "totalExpenses": round(total_expenses, 2),
        "netBalance": round(net_balance, 2),
        "savingsRate": round(savings_rate, 1),
        "averageDailySpending": round(avg_daily_spending, 2),
        "budgetCompliance": 0.0,
        "period": period
    }


async def get_expense_analysis_by_period(
        db: AsyncSession,
        user_id: int,
        period: str
) -> List[Dict]:
    """
    Get expense analysis by category for a specific period.
    """
    end_date = date.today()

    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    breakdown = await get_category_spending_breakdown(db, user_id, start_date, end_date)

    # Transform data to match frontend expectations
    analysis = []
    total_spent = sum(item['totalSpent'] for item in breakdown)

    for item in breakdown:
        analysis.append({
            "category": item['categoryName'],
            "amount": abs(item['totalSpent']),
            "percentage": round((abs(item['totalSpent']) / total_spent * 100), 1) if total_spent > 0 else 0,
            "trend": "up",  # TODO: Implement trend calculation based on historical data
            "change": 0.0,  # TODO: Implement change calculation
            "budgetAmount": item.get('budgetAmount'),
            "previousAmount": None  # TODO: Implement previous period comparison
        })

    return sorted(analysis, key=lambda x: x['amount'], reverse=True)


async def get_income_analysis_by_period(
        db: AsyncSession,
        user_id: int,
        period: str
) -> List[Dict]:
    """
    Get income analysis by category for a specific period.
    """
    end_date = date.today()

    if period == "week":
        start_date = end_date - timedelta(days=7)
        month = None
        year = None
    elif period == "month":
        start_date = end_date - timedelta(days=30)
        month = end_date.month
        year = end_date.year
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
        month = None
        year = end_date.year
    elif period == "year":
        start_date = end_date - timedelta(days=365)
        month = None
        year = end_date.year
    else:
        start_date = end_date - timedelta(days=30)
        month = end_date.month
        year = end_date.year

    # Get category data
    category_data = await get_category_chart_data(db, user_id, month, year)

    # Filter only income categories
    total_income = sum(item['incomes'] for item in category_data if item['incomes'] > 0)

    analysis = []
    for item in category_data:
        if item['incomes'] > 0:
            analysis.append({
                "category": item['category'],
                "amount": round(item['incomes'], 2),
                "percentage": round((item['incomes'] / total_income * 100), 1) if total_income > 0 else 0,
                "trend": "up",  # TODO: Implement trend calculation
                "change": 0.0,  # TODO: Implement change calculation
                "previousAmount": None  # TODO: Implement previous period comparison
            })

    return sorted(analysis, key=lambda x: x['amount'], reverse=True)


async def get_trend_analysis_by_period(
        db: AsyncSession,
        user_id: int,
        period: str,
        granularity: str = "monthly"
) -> List[Dict]:
    """
    Get trend analysis for income, expenses and balance.
    """
    from app.services.metrics_service import get_monthly_chart_data

    # Determine number of months based on period
    if period == "week":
        months = 1
    elif period == "month":
        months = 3
    elif period == "quarter":
        months = 6
    elif period == "year":
        months = 12
    else:
        months = 6

    monthly_data = await get_monthly_chart_data(db, user_id, months)

    # Transform data to match frontend expectations
    trends = []
    for item in monthly_data:
        trends.append({
            "period": item['month'],
            "income": round(item['incomes'], 2),
            "expenses": round(item['expenses'], 2),
            "balance": round(item['balance'], 2),
            "savings": round(item['incomes'] - item['expenses'], 2)
        })

    return trends


async def export_report_by_filters(
        db: AsyncSession,
        user_id: int,
        filters: Dict,
        format_type: str
) -> tuple[any, str]:
    """
    Export report based on filters and format.
    """
    date_range = filters.get('dateRange', 'month')

    # Calculate dates
    end_date = date.today()

    if date_range == "week":
        start_date = end_date - timedelta(days=7)
    elif date_range == "month":
        start_date = end_date - timedelta(days=30)
    elif date_range == "quarter":
        start_date = end_date - timedelta(days=90)
    elif date_range == "year":
        start_date = end_date - timedelta(days=365)
    elif date_range == "custom":
        start_date_str = filters.get('startDate')
        end_date_str = filters.get('endDate')
        if start_date_str:
            start_date = date.fromisoformat(start_date_str)
        else:
            start_date = end_date - timedelta(days=30)
        if end_date_str:
            end_date = date.fromisoformat(end_date_str)
    else:
        start_date = end_date - timedelta(days=30)

    # Generate the base report
    report_data = await generate_report(db, user_id, start_date, end_date)

    if format_type == 'pdf':
        pdf_file = await generate_pdf_report(report_data)
        filename = f"financial_report_{date_range}_{start_date}_{end_date}.pdf"
        return pdf_file, filename
    elif format_type == 'json':
        # Para JSON, preparar un reporte completo con todos los datos

        period_str = date_range if date_range != "custom" else "month"

        try:
            financial_summary = await get_financial_summary_by_period(db, user_id, period_str)
        except:
            financial_summary = None

        try:
            expense_analysis = await get_expense_analysis_by_period(db, user_id, period_str)
        except:
            expense_analysis = []

        try:
            income_analysis = await get_income_analysis_by_period(db, user_id, period_str)
        except:
            income_analysis = []

        try:
            trend_data = await get_trend_analysis_by_period(db, user_id, period_str, "monthly")
        except:
            trend_data = []

        # Construir el objeto JSON completo
        json_data = {
            "summary": {
                "totalIncome": report_data.total_income,
                "totalExpenses": report_data.total_expenses,
                "netBalance": report_data.net_balance,
                "savingsRate": financial_summary.get('savingsRate', 0) if financial_summary else 0,
                "averageDailySpending": financial_summary.get('averageDailySpending', 0) if financial_summary else 0,
                "budgetCompliance": financial_summary.get('budgetCompliance', 0) if financial_summary else 0,
                "period": f"{start_date} to {end_date}"
            },
            "expenseAnalysis": expense_analysis,
            "incomeAnalysis": income_analysis,
            "trends": trend_data,
            "categoryBreakdown": [
                {
                    "category": cat.category,
                    "amount": abs(cat.net_category_balance),
                    "percentage": 0,  # Se puede calcular si es necesario
                    "trend": "up" if cat.net_category_balance > 0 else "down",
                    "change": 0
                }
                for cat in report_data.top_categories
            ],
            "transactions": [
                {
                    "id": tx.id,
                    "amount": tx.amount,
                    "description": tx.description,
                    "date": str(tx.report_date),
                    "category": tx.category
                }
                for tx in report_data.transactions[:50]  # Limitar a 50 transacciones
            ],
            "generatedAt": date.today().isoformat(),
            "filters": {
                "dateRange": date_range,
                "startDate": str(start_date),
                "endDate": str(end_date),
                "reportType": filters.get('reportType', 'comprehensive')
            }
        }

        filename = f"financial_report_{date_range}_{start_date}_{end_date}.json"
        return json_data, filename
    else:
        raise ValueError(f"Unsupported format: {format_type}")