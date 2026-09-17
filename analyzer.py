import json
import re
from freeflow_llm import FreeFlowClient, NoProvidersAvailableError


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

КРИТИЧЕСКИ ВАЖНО:
- Ответ должен быть ПОЛНЫМ JSON-объектом, начиная с { и заканчивая }.
- НЕ обрывай ответ на середине.
- Поле "reason" должно быть коротким (до 100 символов).

Правила сетапа:
- Ищем ТРЕНД на 4-часовом таймфрейме (цена выше/ниже EMA 200).
- Ждём ОТКАТ к EMA 50 или уровню поддержки/сопротивления.
- Stop — за локальный минимум/максимум + буфер 0.5%.
- ВАЖНО: расстояние от входа до стопа должно быть НЕ МЕНЬШЕ 1.5% от цены входа.
- Take = минимум 1.5R, максимум 3R.
- Если чёткого тренда с откатом нет — верни side: "NONE".
"""


def _extract_json(text: str) -> dict | None:
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

    if text.startswith("{"):
        for closer in ["}", '"}', '"]}', '"}]}']:
            try:
                return json.loads(text + closer)
            except json.JSONDecodeError:
                continue

    return None


async def analyze_coin(symbol: str, timeframe: str, market_data: str) -> dict:
    try:
        with FreeFlowClient() as client:
            response = client.chat(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": market_data},
                ],
                model="openai/gpt-oss-120b",  # Groq — актуальная модель
                temperature=0.2,
                max_tokens=1000,
            )
        content = response.content

        parsed = _extract_json(content)
        if parsed is None:
            return {"error": "Не удалось распарсить JSON", "raw": content[:150]}

        return parsed

    except NoProvidersAvailableError:
        # Пробуем Gemini с актуальной моделью
        try:
            with FreeFlowClient() as client:
                response = client.chat(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": market_data},
                    ],
                    model="gemini-3.6-flash",  # Gemini — актуальная модель
                    temperature=0.2,
                    max_tokens=1000,
                )
            content = response.content
            parsed = _extract_json(content)
            if parsed is None:
                return {"error": "Не удалось распарсить JSON", "raw": content[:150]}
            return parsed
        except Exception as e:
            return {"error": f"Все провайдеры недоступны: {str(e)[:100]}"}
    except Exception as e:
        return {"error": str(e)[:150]}
    
