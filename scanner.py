import asyncio
from analyzer import analyze_coin
from database import save_signal
from config import MIN_RR, MAX_RR, TRADE_TYPES, SIGNAL_EMOJI
from telegram import Bot
from config import CHANNEL_ID

# Сокращённый список монет, чтобы не сжигать лимит Groq
TOP_COINS_LIST = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT"
]

async def get_top_volume_coins():
    return TOP_COINS_LIST

async def scan_once(bot: Bot):
    coins = await get_top_volume_coins()
    print(f"Сканируем {len(coins)} монет...")

    # Пока тестируем только скальп, чтобы экономить лимиты
    trade_types_to_scan = {
        "scalp": TRADE_TYPES["scalp"]
    }

    for trade_type, meta in trade_types_to_scan.items():
        for symbol in coins:
            try:
                market_data = f"Монета: {symbol}. Таймфрейм: {meta['tf']}. Сделай технический анализ на основе текущей рыночной ситуации."
                
                result = analyze_coin(symbol, meta["tf"], market_data)

                if "error" in result:
                    print(f"Ошибка анализа {symbol}: {result['error']}")
                    continue

                rr = float(result.get("rr", 0))
                if not (MIN_RR <= rr <= MAX_RR):
                    continue

                data = {
                    "symbol": symbol,
                    "trade_type": trade_type,
                    "side": result.get("side", "LONG"),
                    "entry": result.get("entry", 0),
                    "stop": result.get("stop", 0),
                    "take": result.get("take", 0),
                    "rr": rr,
                    "strength": result.get("strength", "medium"),
                    "reason
