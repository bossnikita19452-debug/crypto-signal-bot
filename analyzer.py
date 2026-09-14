from openai import OpenAI
from config import GROQ_API_KEY
import json

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

def analyze_coin(symbol: str, timeframe: str, market_data: str) -> dict:
    prompt = f"""
Ты профессиональный крипто-трейдер.
Проанализируй {symbol} на таймфрейме {timeframe}.

Данные рынка:
{market_data}

Верни ТОЛЬКО валидный JSON без лишнего текста:
{{
  "side": "LONG" или "SHORT",
  "entry": число,
  "stop": число,
  "take": число,
  "rr": число,
  "strength": "strong" или "medium" или "weak",
  "reason": "краткое обоснование на русском (1-2 предложения)"
}}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}
