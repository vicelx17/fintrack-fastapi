from datetime import date
from io import BytesIO
from typing import Optional

from matplotlib import pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction
from app.schemas.report_schema import ReportResponse, ReportTransaction, ReportCategory


async def generate_report(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None) -> ReportResponse:

    query = select(Transaction).options(selectinload(Transaction.category)).where(Transaction.user_id == user_id)

    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)

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
            date=transaction.date,
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
        # Limitar a las primeras 20 transacciones para evitar PDFs muy largos
        for tx in report_data.transactions[:20]:
            transactions_data.append(
                [str(tx.date), tx.description[:30] + "..." if len(tx.description) > 30 else tx.description,
                 f"${tx.amount:.2f}", tx.category]
            )

        if len(report_data.transactions) > 20:
            transactions_data.append(["...", f"and {len(report_data.transactions) - 20} more transactions", "", ""])
    else:
        transactions_data = [["Date", "Description", "Amount", "Category"],
                             ["No transactions", "available", "$0.00", "N/A"]]

    transactions_table = Table(
        transactions_data,
        colWidths=[1.5 * inch, 2.5 * inch, 1 * inch, 1.5 * inch]
    )

    # AQUÍ ESTÁ EL FIX PRINCIPAL - COLORES VERDES Y ESPACIADO ARREGLADO
    transactions_table.setStyle(
        TableStyle(
            [
                # HEADER - Verde oscuro profesional (SIN espacio extra)
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