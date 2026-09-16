import json
import re
from openai import AsyncOpenAI
from config import GROQ_API_KEY, GROQ_MODEL

client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

SYSTEM_PROMPT = """Ты — профессиональный крипто-аналитик, работающий с трендовыми стратегиями.

Найди сетап для СРЕДНЕСРОЧНОЙ торговли (удержание от нескольких часов до нескольких дней).

Ответь ТОЛЬКО валидным JSON без лишнего текста. Формат:
{
  "side": "LONG" | "SHORT" | "NONE",
  "strength": "strong" | "medium" | "weak",
  "entry": число,
  "stop": число,
  "take": число,
  "rr": число,
  "reason": "краткое объяснение на русском"
}

Правила:
- Ищем ТРЕНД на 4-часовом таймфрейме (цена выше/ниже EMA 200).
- Ждём ОТКАТ к EMA 50 или уровню поддержки/сопротивления.
- Stop — за локальный минимум/максимум + буфер 0.5%.
- Take = минимум 1.5R, максимум 3R.
- Если чёткого тренда с откатом нет — верни side: "NONE".
"""


def _extract_json(text: str) -> dict | None:
    """Вытащить JSON из ответа модели."""
    if not text:
        return None

    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


async def analyze_coin(symbol: str, timeframe: str, market_data: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": market_data},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        content = response.choices[0].message.content

        parsed = _extract_json(content)
        if parsed is None:
            return {"error": "Не удалось распарсить JSON", "raw": content[:100]}

        return parsed

    except Exception as e:
        return {"error": str(e)[:100]}
    
