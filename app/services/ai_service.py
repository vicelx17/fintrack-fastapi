import json
import os
import re
from datetime import date
from typing import Dict, List

import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction

load_dotenv()

genai.configure(api_key=os.getenv("GENAI_API_KEY"))


async def predict_future_transactions(user_transactions: list[dict]) -> dict:
    """
    Predict future transaction for the logged-in user using Gemini AI.
    """
    prompt = f"""
    You are an expert financial assistant AI. Analyze the user's past transactions and predict possible future transactions.

    IMPORTANT: Return ONLY valid JSON, no markdown, no explanations, no code blocks.

    Expected JSON structure:
    {{
      "predictions": [
        {{
          "description": "string",
          "amount": number,
          "date": "YYYY-MM-DD",
          "category": "string",
          "confidence": number_between_0_and_1
        }}
      ]
    }}

    User transactions: {user_transactions}
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    return extract_json_from_response(response.text)


async def generate_financial_insights(
        transactions: list[Dict],
        budgets: list[Dict],
        financial_summary: Dict
) -> Dict:
    """
        Generate comprehensive financial insights including:
        - Spending pattern analysis
        - Budget alerts
        - Savings recommendations
        - Future predictions
    """

    # AI Context
    total_income = financial_summary.get('monthly_income', 0)
    total_expenses = financial_summary.get('monthly_expenses', 0)
    balance = financial_summary.get('total_balance', 0)

    category_expenses = {}
    for tx in transactions:
        if tx['amount'] < 0:
            category = tx.get('category')
            category_expenses[category] = category_expenses.get(category, 0) + abs(tx['amount'])

    budget_status = []
    for budget in budgets:
        if budget.get('status') == 'over':
            budget_status.append({
                'category': budget['category'],
                'amount': budget['spent'],
                'budget': budget['budget'],
                'exceeded_by': budget['spent'] - budget['budget']
            })
    prompt = f"""
    Eres un asesor financiero experto. Analiza la situación financiera del usuario y genera insights útiles en ESPAÑOL.

    CONTEXTO FINANCIERO:
    - Balance total: €{balance:.2f}
    - Ingresos mensuales: €{total_income:.2f}
    - Gastos mensuales: €{total_expenses:.2f}
    - Tasa de ahorro: {((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0:.1f}%

    GASTOS POR CATEGORÍA:
    {json.dumps(category_expenses, indent=2)}

    PRESUPUESTOS EXCEDIDOS:
    {json.dumps(budget_status, indent=2)}

    TRANSACCIONES RECIENTES (últimas 10):
    {json.dumps(transactions[:10], indent=2)}

    INSTRUCCIONES:
    Genera exactamente 3 insights financieros relevantes. DEBE SER JSON VÁLIDO SIN MARKDOWN.
    
    Tipos de insights:
    1. "prediction" - Predicción de gasto basada en patrones
    2. "warning" - Alerta sobre presupuestos o gastos excesivos
    3. "tip" - Recomendación de ahorro u optimización
    
    Niveles de confianza:
    - "Alta" - Basado en datos claros y patrones consistentes
    - "Media" - Estimación razonable con algo de incertidumbre
    - "Crítico" - Alerta urgente que requiere atención inmediata

    FORMATO DE RESPUESTA (JSON puro, sin ```json ni explicaciones):
    {{
      "insights": [
        {{
          "type": "prediction|warning|tip",
          "title": "Título corto en español",
          "message": "Mensaje detallado explicando el insight",
          "confidence": "Alta|Media|Crítico",
          "icon": "brain|alert-triangle|lightbulb",
          "color": "primary|destructive|secondary",
          "amount": número opcional si aplica,
          "category": "categoría opcional si aplica"
        }}
      ]
    }}

    GENERA INSIGHTS ESPECÍFICOS Y ÚTILES BASADOS EN LOS DATOS REALES DEL USUARIO.
    """

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        result = extract_json_from_response(response.text)

        if "insights" not in result:
            return generate_fallback_insights(financial_summary, budget_status, category_expenses)

        return result

    except Exception as e:
        print(f"Error generando insights: con IA: {e}")
        return generate_fallback_insights(financial_summary, budget_status, category_expenses)


def generate_fallback_insights(financial_summary: Dict, budget_status: List, category_expenses: Dict) -> Dict:
    """
    Generate basic insights when AI fail, based on rules
    """
    insights = []

    total_income = financial_summary.get('monthly_income', 0)
    total_expenses = financial_summary.get('monthly_expenses', 0)

    if total_expenses > 0:
        next_month_prediction = total_expenses * 1.05
        insights.append({
            "type": "prediction",
            "title": "Predicción de Gastos",
            "message": f"Basado en tu patrón, gastarás aproximadamente €{next_month_prediction:.2f} este mes",
            "confidence": "Media",
            "icon": "brain",
            "color": "primary",
            "amount": next_month_prediction
        })

    if budget_status:
        budget_alert = budget_status[0]
        insights.append({
            "type": "warning",
            "title": "Alerta de Presupuesto",
            "message": f"{budget_alert['category']} excedió el límite en €{budget_alert['exceeded_by']:.2f}",
            "confidence": "Crítico",
            "icon": "alert-triangle",
            "color": "destructive",
            "amount": budget_alert['exceeded_by'],
            "category": budget_alert['category']
        })
    elif total_expenses > total_income * 0.9:
        insights.append({
            "type": "warning",
            "title": "Gastos Elevados",
            "message": f"Tus gastos representan el {(total_expenses / total_income * 100) if total_income > 0 else 0:.1f}% de tus ingresos",
            "confidence": "Alta",
            "icon": "alert-triangle",
            "color": "destructive"
        })
    if category_expenses:
        highest_category = max(category_expenses.items(), key=lambda x: x[1])
        potential_saving = highest_category[1] * 0.15
        insights.append({
            "type": "tip",
            "title": "Oportunidad de Ahorro",
            "message": f"Podrías ahorrar €{potential_saving:.2f}/mes optimizando gastos en {highest_category[0]}",
            "confidence": "Media",
            "icon": "lightbulb",
            "color": "secondary",
            "amount": potential_saving,
            "category": highest_category[0]
        })
    else:
        insights.append({
            "type": "tip",
            "title": "Consejo Financiero",
            "message": "Establece presupuestos por categoría para controlar mejor tus gastos",
            "confidence": "Alta",
            "icon": "lightbulb",
            "color": "secondary"
        })

    return {"insights": insights}


def extract_json_from_response(text: str) -> dict:
    text = text.strip()

    json_pattern = r'\{.* \}'
    json_match = re.search(json_pattern, text, re.DOTALL)

    if json_match:
        json_text = json_match.group()
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "error": "Could not parse AI response as JSON",
            "raw_response": text,
            "parsing_error": str(e)
        }


async def analyze_spending_trends(transactions: List[Dict]) -> Dict:
    """
    Analyze spending trends over time
    """
    if not transactions:
        return {"trend": "neutral", "message": "No hay suficientes datos"}

    from collections import defaultdict
    weekly_spending = defaultdict(float)

    for tx in transactions:
        if tx['amount'] < 0:
            tx_date = date.fromisoformat(tx['date'])
            week = tx_date.isocalendar()[1]
            weekly_spending[week] += abs(tx['amount'])

        if len(weekly_spending) < 2:
            return {"trend": "neutral", "message": "Necesitas más historial"}

        weeks = sorted(weekly_spending.items())
        recent_avg = sum(w[1] for w in weeks[-2:]) / 2
        older_avg = sum(w[1] for w in weeks[:-2]) / max(len(weeks) - 2, 1)

        if recent_avg > older_avg * 1.2:
            return {
                "trend": "increasing",
                "message": f"Tus gastos han aumentado un {(recent_avg / older_avg - 1) * 100:.1f}% recientemente",
                "percentage": (recent_avg / older_avg - 1) * 100
            }
        elif recent_avg < older_avg * 0.8:
            return {
                "trend": "decreasing",
                "message": f"¡Bien! Has reducido tus gastos un {((1 - recent_avg / older_avg) * 100):.1f}%",
                "percentage": (1 - recent_avg / older_avg) * 100
            }
        else:
            return {
                "trend": "stable",
                "message": "Tus gastos se mantienen estables",
                "percentage": 0
            }

async def get_ai_insights_data(db: AsyncSession, user_id: int) -> Dict:
    """
    Prepare data for AI insights
    """
    recent_transactions = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc())
        .limit(100)
    )

    transactions_data = []
    for transaction in recent_transactions.scalars():
        transactions_data.append({
            "id": transaction.id,
            "amount": float(transaction.amount),
            "description": transaction.description,
            "date": transaction.transaction_date.isoformat(),
            "category": transaction.category.name
        })

    return {
        "transactions": transactions_data,
        "user": user_id
    }
