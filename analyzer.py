import json
import re
from freeflow_llm import FreeFlowClient, NoProvidersAvailableError


SYSTEM_PROMPT = """Ты — профессиональный крипто-аналитик, работающий с трендовыми стратегиями.

Найди сетап для СРЕДНЕСРОЧНОЙ торговли (удержание от нескольких часов до нескольких дней).

Ответь ТОЛЬКО валидным JSON без лишнего текста. Формат:
{
  "side": "LONG" | "SHORT" | "NONE",
  "strength": "strong" | "medium" | "weak",
  "stop": число,
  "take": число,
  "reason": "краткое объяснение на русском"
}

КРИТИЧЕСКИ ВАЖНО:
- Ответ должен быть ПОЛНЫМ JSON-объектом, начиная с { и заканчивая }.
- НЕ обрывай ответ на середине.
- Поле "reason" должно быть коротким (до 100 символов).

Правила сетапа:
- Ищем ТРЕНД на 4-часовом таймфрейме (цена выше/ниже EMA 200).
- Вход должен быть СРАЗУ по текущей цене (market entry).
- ВАЖНО: расстояние от входа до стопа должно быть НЕ МЕНЬШЕ 1.5% от цены входа.
- Take = минимум 1.5R, максимум 3R.
- Если чёткого подтверждения для входа по рынку нет — верни side: "NONE".
- Если новости резко негативные для LONG — верни side: "NONE".
- Если Fear & Greed в зоне Extreme Greed (>75) — не давай LONG.
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


async def analyze_coin(symbol: str, market_data: str) -> dict:
    try:
        with FreeFlowClient() as client:
            response = client.chat(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": market_data},
                ],
                model="openai/gpt-oss-120b",
                temperature=0.2,
                max_tokens=1000,
            )
        content = response.content
        parsed = _extract_json(content)
        if parsed is None:
            return {"error": "Не удалось распарсить JSON", "raw": content[:150]}
        return parsed
    except NoProvidersAvailableError:
        try:
            with FreeFlowClient() as client:
                response = client.chat(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": market_data},
                    ],
                    model="gemini-3.6-flash",
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
    
