from datetime import date, timedelta, datetime
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


async def generate_pdf_report(
        report_data: ReportResponse,
        filters: Optional[Dict] = None,
        financial_summary: Optional[Dict] = None,
        expense_analysis: Optional[List[Dict]] = None,
        income_analysis: Optional[List[Dict]] = None,
        trend_data: Optional[List[Dict]] = None
) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)

    styles = getSampleStyleSheet()
    elements = []

    report_type = filters.get('reportType', 'comprehensive') if filters else 'comprehensive'
    transaction_limit = filters.get('transactionLimit') if filters else None

    # ---- Header ----
    title_style = styles["Title"]
    title = Paragraph("FinTrack - Reporte Financiero", title_style)
    elements.append(title)

    current_date = date.today().strftime("%d/%m/%Y")

    # Mostrar período del reporte
    period_text = ""
    if filters:
        date_range = filters.get('dateRange', 'month')
        if date_range == "custom":
            start = filters.get('startDate', '')
            end = filters.get('endDate', '')
            period_text = f"Período: {start} al {end}"
        else:
            period_map = {
                'week': 'Última semana',
                'month': 'Último mes',
                'quarter': 'Último trimestre',
                'year': 'Último año'
            }
            period_text = f"Período: {period_map.get(date_range, 'Personalizado')}"

    elements.append(Paragraph(f"Generado el: {current_date}", styles["Normal"]))
    if period_text:
        elements.append(Paragraph(period_text, styles["Normal"]))

    # Mostrar tipo de reporte
    report_type_map = {
        'comprehensive': 'Completo',
        'expenses': 'Solo Gastos',
        'income': 'Solo Ingresos',
        'budgets': 'Presupuestos',
        'trends': 'Tendencias'
    }
    elements.append(Paragraph(f"Tipo de reporte: {report_type_map.get(report_type, 'Completo')}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    # ---- Summary Section ----
    summary_data = [["Métrica", "Valor"]]

    if report_type in ['comprehensive', 'income']:
        summary_data.append(["Ingresos Totales", f"€{report_data.total_income:.2f}"])

    if report_type in ['comprehensive', 'expenses']:
        summary_data.append(["Gastos Totales", f"€{report_data.total_expenses:.2f}"])

    if report_type == 'comprehensive':
        summary_data.append(["Balance Neto", f"€{report_data.net_balance:.2f}"])

    # Agregar métricas adicionales si están disponibles
    if financial_summary:
        if report_type in ['comprehensive', 'income'] and financial_summary.get('savingsRate'):
            summary_data.append(["Tasa de Ahorro", f"{financial_summary['savingsRate']:.1f}%"])
        if report_type in ['comprehensive', 'expenses'] and financial_summary.get('averageDailySpending'):
            summary_data.append(["Gasto Diario Promedio", f"€{financial_summary['averageDailySpending']:.2f}"])
        if financial_summary.get('budgetCompliance') and report_type in ['comprehensive', 'budgets']:
            summary_data.append(["Cumplimiento Presupuesto", f"{financial_summary['budgetCompliance']:.1f}%"])

    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f7f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#2d5a3d")),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(Paragraph("Resumen Financiero", styles["Heading2"]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ---- Separar ingresos y gastos por categoría ----
    income_categories = []
    expense_categories = []

    for cat in report_data.top_categories:
        if cat.net_category_balance > 0:
            income_categories.append(cat)
        else:
            expense_categories.append(cat)

    # ---- Gráfico de Ingresos ----
    if income_categories and report_type in ['comprehensive', 'income']:
        try:
            buffer_income = BytesIO()

            categories = [cat.category for cat in income_categories]
            amounts = [float(cat.net_category_balance) for cat in income_categories]

            plt.figure(figsize=(8, 4.5))
            bars = plt.bar(categories, amounts, color="#2d5a3d", edgecolor="#1a472a", linewidth=1.5)

            max_amount = max(amounts)
            for bar, amount in zip(bars, amounts):
                plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_amount * 0.02,
                         f'€{amount:.2f}', ha='center', va='bottom', fontsize=10, color="#1a472a", fontweight='bold')

            plt.title("Ingresos por Categoría", fontsize=14, fontweight="bold", color="#1a472a", pad=20)
            plt.xlabel("Categorías", fontsize=12, color="#2d5a3d")
            plt.ylabel("Cantidad (€)", fontsize=12, color="#2d5a3d")
            plt.xticks(rotation=45, ha="right", color="#2d5a3d")
            plt.yticks(color="#2d5a3d")
            plt.ylim(0, max_amount * 1.15)  # Agregar espacio arriba para las etiquetas
            plt.tight_layout()

            plt.savefig(buffer_income, format="png", dpi=100, bbox_inches='tight')
            plt.close()

            buffer_income.seek(0)
            income_image = Image(buffer_income, width=5 * inch, height=2.8 * inch)
            elements.append(Paragraph("Ingresos por Categoría", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(income_image)
            elements.append(Spacer(1, 0.3 * inch))

        except Exception as e:
            print(f"Error generando gráfico de ingresos: {e}")

    # ---- Gráfico de Gastos ----
    if expense_categories and report_type in ['comprehensive', 'expenses']:
        try:
            buffer_expense = BytesIO()

            categories = [cat.category for cat in expense_categories]
            amounts = [abs(float(cat.net_category_balance)) for cat in expense_categories]

            plt.figure(figsize=(8, 4.5))
            bars = plt.bar(categories, amounts, color="#dc2626", edgecolor="#991b1b", linewidth=1.5)

            max_amount = max(amounts)
            for bar, amount in zip(bars, amounts):
                plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_amount * 0.02,
                         f'€{amount:.2f}', ha='center', va='bottom', fontsize=10, color="#991b1b", fontweight='bold')

            plt.title("Gastos por Categoría", fontsize=14, fontweight="bold", color="#991b1b", pad=20)
            plt.xlabel("Categorías", fontsize=12, color="#dc2626")
            plt.ylabel("Cantidad (€)", fontsize=12, color="#dc2626")
            plt.xticks(rotation=45, ha="right", color="#dc2626")
            plt.yticks(color="#dc2626")
            plt.ylim(0, max_amount * 1.15)  # Agregar espacio arriba para las etiquetas
            plt.tight_layout()

            plt.savefig(buffer_expense, format="png", dpi=100, bbox_inches='tight')
            plt.close()

            buffer_expense.seek(0)
            expense_image = Image(buffer_expense, width=5 * inch, height=2.8 * inch)
            elements.append(Paragraph("Gastos por Categoría", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(expense_image)
            elements.append(Spacer(1, 0.3 * inch))

        except Exception as e:
            print(f"Error generando gráfico de gastos: {e}")

    # ---- Análisis de Presupuestos ----
    if report_type in ['comprehensive', 'budgets'] and expense_analysis:
        elements.append(Paragraph("Análisis de Presupuestos", styles["Heading2"]))

        budget_data = [["Categoría", "Gastado", "Presupuesto", "% Usado"]]
        for item in expense_analysis[:10]:
            if item.get('budgetAmount'):
                budget_amount = item['budgetAmount']
                spent = item['amount']
                percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0
                budget_data.append([
                    item['category'],
                    f"€{spent:.2f}",
                    f"€{budget_amount:.2f}",
                    f"{percentage:.1f}%"
                ])

        if len(budget_data) > 1:
            budget_table = Table(budget_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1 * inch])
            budget_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f7f1")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#2d5a3d")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            elements.append(budget_table)
            elements.append(Spacer(1, 0.3 * inch))

    # ---- Análisis de Ingresos por Categoría ----
    if report_type in ['comprehensive', 'income'] and income_analysis:
        elements.append(Paragraph("Análisis de Ingresos por Categoría", styles["Heading2"]))

        income_data = [["Categoría", "Cantidad", "% del Total"]]
        for item in income_analysis[:10]:
            income_data.append([
                item['category'],
                f"€{item['amount']:.2f}",
                f"{item['percentage']:.1f}%"
            ])

        if len(income_data) > 1:
            income_table = Table(income_data, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
            income_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f7f1")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#2d5a3d")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            elements.append(income_table)
            elements.append(Spacer(1, 0.3 * inch))

    # ---- Análisis de Tendencias ----
    if report_type in ['comprehensive', 'trends'] and trend_data and len(trend_data) > 0:
        try:
            buffer_trend = BytesIO()

            periods = [item['period'] for item in trend_data]
            incomes = [item['income'] for item in trend_data]
            expenses = [item['expenses'] for item in trend_data]

            plt.figure(figsize=(8, 4))
            plt.plot(periods, incomes, marker='o', color="#2d5a3d", linewidth=2, label='Ingresos')
            plt.plot(periods, expenses, marker='o', color="#dc2626", linewidth=2, label='Gastos')

            plt.title("Tendencias Financieras", fontsize=14, fontweight="bold", color="#1a472a")
            plt.xlabel("Período", fontsize=12)
            plt.ylabel("Cantidad (€)", fontsize=12)
            plt.xticks(rotation=45, ha="right")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()

            plt.savefig(buffer_trend, format="png", dpi=100, bbox_inches='tight')
            plt.close()

            buffer_trend.seek(0)
            trend_image = Image(buffer_trend, width=5 * inch, height=2.5 * inch)
            elements.append(Paragraph("Tendencias Financieras", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(trend_image)
            elements.append(Spacer(1, 0.3 * inch))

        except Exception as e:
            print(f"Error generando gráfico de tendencias: {e}")

    # ---- Tabla de Top Categorías ----
    if report_data.top_categories and report_type == 'comprehensive':
        elements.append(Paragraph("Resumen por Categorías", styles["Heading2"]))

        top_categories_data = [["Categoría", "Balance Neto", "Tipo"]]
        for cat in report_data.top_categories[:10]:
            tipo = "Ingreso" if cat.net_category_balance > 0 else "Gasto"
            top_categories_data.append([
                cat.category,
                f"€{cat.net_category_balance:.2f}",
                tipo
            ])

        top_categories_table = Table(top_categories_data, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        top_categories_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f7f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#2d5a3d")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )

        elements.append(top_categories_table)
        elements.append(Spacer(1, 0.3 * inch))

    # ---- Tabla de Transacciones ----
    elements.append(Paragraph("Transacciones", styles["Heading2"]))

    if transaction_limit:
        elements.append(Paragraph(f"Mostrando {transaction_limit} transacciones", styles["Normal"]))

    elements.append(Spacer(1, 0.05 * inch))

    if report_data.transactions:
        # Filtrar transacciones según el tipo de reporte
        filtered_transactions = report_data.transactions

        if report_type == 'expenses':
            filtered_transactions = [tx for tx in filtered_transactions if tx.amount < 0]
        elif report_type == 'income':
            filtered_transactions = [tx for tx in filtered_transactions if tx.amount > 0]

        # Aplicar límite de transacciones
        limit = transaction_limit if transaction_limit else len(filtered_transactions)
        transactions_to_show = filtered_transactions[:limit]

        transactions_data = [["Fecha", "Descripción", "Cantidad", "Categoría"]]
        for tx in transactions_to_show:
            formatted_date = tx.report_date.strftime("%d/%m/%Y")
            desc = tx.description[:35] + "..." if len(tx.description) > 35 else tx.description
            transactions_data.append([
                formatted_date,
                desc,
                f"€{tx.amount:.2f}",
                tx.category
            ])

        if len(filtered_transactions) > limit:
            remaining = len(filtered_transactions) - limit
            transactions_data.append(["...", f"y {remaining} transacciones más", "", ""])
    else:
        transactions_data = [
            ["Fecha", "Descripción", "Cantidad", "Categoría"],
            ["Sin transacciones", "disponibles", "€0.00", "N/A"]
        ]

    transactions_table = Table(
        transactions_data,
        colWidths=[1.2 * inch, 2.5 * inch, 1.1 * inch, 1.7 * inch]
    )

    transactions_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a472a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fdf9"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2d5a3d")),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    elements.append(transactions_table)

    # ---- Footer ----
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph(
            f"© {datetime.now().year} FinTrack - Herramienta de Gestión Financiera Personal",
            styles["Normal"]
        )
    )

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
        # Obtener datos adicionales para el PDF
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
            trend_data = await get_trend_analysis_by_period(db, user_id, period_str)
        except:
            trend_data = []

        pdf_file = await generate_pdf_report(
            report_data,
            filters=filters,
            financial_summary=financial_summary,
            expense_analysis=expense_analysis,
            income_analysis=income_analysis,
            trend_data=trend_data
        )
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
            trend_data = await get_trend_analysis_by_period(db, user_id, period_str)
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