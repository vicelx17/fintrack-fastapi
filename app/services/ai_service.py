import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

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

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    def extract_json_from_response(text: str) -> dict:
        text = text.strip()

        json_pattern = r'\{.*\}'
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
    return extract_json_from_response(response.text)