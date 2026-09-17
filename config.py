import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ─────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# ─── CoinGecko ────────────────────────────────────────────────────
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

# ─── ИИ провайдеры ────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ─── Параметры сканирования ───────────────────────────────────────
SCAN_INTERVAL_HOURS = 1

# ─── Группировка монет ────────────────────────────────────────────
USE_GROUPS = True
NUM_GROUPS = 2

# ─── Флаг активности сканера ──────────────────────────────────────
SCANNING_ENABLED = True

# ─── Соотношение риск/прибыль ─────────────────────────────────────
MIN_RR = 1.5
MAX_RR = 3.0

# ─── Фильтры ──────────────────────────────────────────────────────
ADX_MIN = 25            # Минимальный ADX (сила тренда)
ATR_MIN_PCT = 0.8       # Минимальная волатильность (ATR %)
ATR_MAX_PCT = 6.0       # Максимальная волатильность
MIN_STOP_PCT = 1.5      # Минимальный стоп

# ─── Журнал «токсичных» монет ─────────────────────────────────────
TOXIC_STREAK = 3            # Сколько убытков подряд = монета в «токсичных»
TOXIC_COOLDOWN_HOURS = 24   # Сколько часов не сканировать «токсичные»

# ─── Типы сделок ──────────────────────────────────────────────────
TRADE_TYPES = {
    "swing": {
        "name": "Среднесрок (тренд)",
        "tf": "4h",
        "hold_hours": 72,
        "min_rr": 1.5,
        "max_rr": 3.0,
    },
}

SIGNAL_EMOJI = {
    "strong": "🟢",
    "medium": "🟡",
    "weak": "🔴",
}
