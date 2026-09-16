import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ─────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# ─── CoinGecko ────────────────────────────────────────────────────
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

# ─── Groq (ИИ) ────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"

# ─── Параметры сканирования ───────────────────────────────────────
SCAN_INTERVAL_HOURS = 1

# ─── Флаг активности сканера (переключается кнопкой) ──────────────
SCANNING_ENABLED = True

# ─── Соотношение риск/прибыль ─────────────────────────────────────
MIN_RR = 1.5
MAX_RR = 3.0

# ─── Типы сделок (только трендовые) ──────────────────────────────
TRADE_TYPES = {
    "swing": {
        "name": "Среднесрок (тренд)",
        "tf": "4h",
        "hold_hours": 72,
        "min_rr": 1.5,
        "max_rr": 3.0,
    },
}

# ─── Цветовые индикаторы силы ────────────────────────────────────
SIGNAL_EMOJI = {
    "strong": "🟢",
    "medium": "🟡",
    "weak": "🔴",
}
