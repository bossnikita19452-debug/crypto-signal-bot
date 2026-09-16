import json
from openai import AsyncOpenAI
from config import GROQ_API_KEY, GROQ_MODEL

client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

SYSTEM_PROMPT = """Ты — профессиональный крипто-аналитик, работающий с трендовыми стратегиями.

Твоя задача — найти сетап для СРЕДНЕСРОЧНОЙ торговли (удержание от нескольких часов до нескольких дней).

Ты должен ответить ТОЛЬКО валидным JSON без лишнего текста. Формат:
{
  "side": "LONG" | "SHORT" | "NONE",
  "strength": "strong" | "medium" | "weak",
  "entry": число,
  "stop": число,
  "take": число,
  "rr": число,
  "reason": "краткое объяснение на русском"
}

Правила для сетапа:
- Ищем ТРЕНД на 4-часовом таймфрейме (цена выше/ниже EMA 200).
- Ждём ОТКАТ к EMA 50 или уровню поддержки/сопротивления.
- Вход только когда откат завершается (появляется бычья/медвежья свеча).
- Stop ставим за локальный минимум/максимум + буфер 0.5%.
- Take = минимум 1.5R, максимум 3R.
- Если чёткого тренда с откатом нет — верни side: "NONE".

Сила сигнала:
- strong: тренд четкий + откат глубокий + RSI в благоприятной зоне.
- medium: тренд есть, но откат неглубокий или RSI на границе.
- weak: тренд слабый, много противоречий — такие сигналы лучше пропускать.
"""

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
        content = response.choices[0].message.content.strip()
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)[:100]}
