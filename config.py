import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Фильтры
MIN_VOLUME_USD = 50_000
MIN_RR = 1.5
MAX_RR = 3.0
TOP_COINS = 100

TRADE_TYPES = {
    "scalp": {"name": "⚡ Скальп", "tf": "15m", "hold": "минуты–часы"},
    "intraday": {"name": "📅 Интрадей", "tf": "1h", "hold": "1–3 дня"},
    "swing": {"name": "🕊 Свинг", "tf": "4h", "hold": "от недели"}
}

SIGNAL_EMOJI = {
    "strong": "🟢",
    "medium": "🟡",
    "weak": "🔴"
}
