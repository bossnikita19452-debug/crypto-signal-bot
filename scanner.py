import ccxt
import asyncio
from analyzer import analyze_coin
from database import save_signal
from config import MIN_VOLUME_USD, MIN_RR, MAX_RR, TOP_COINS, TRADE_TYPES, SIGNAL_EMOJI
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN, CHANNEL_ID

exchange = ccxt.binance({"enableRateLimit": True})

async def get_top_volume_coins():
    tickers = exchange.fetch_tickers()
    pairs = []
    for symbol, t in tickers.items():
        if symbol.endswith("/USDT") and t.get("quoteVolume"):
            vol = t["quoteVolume"]
            if vol >= MIN_VOLUME_USD:
                pairs.append((symbol, vol))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return [p[0] for p in pairs[:TOP_COINS]]

async def scan_once(bot: Bot):
    coins = await get_top_volume_coins()
    for trade_type, meta in TRADE_TYPES.items():
        for symbol in coins[:30]:  # чтобы не спамить
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, meta["tf"], limit=50)
                market_data = f"Последние свечи: {ohlcv[-5:]}"
                result = analyze_coin(symbol, meta["tf"], market_data)

                if "error" in result:
                    continue

                rr = float(result.get("rr", 0))
                if not (MIN_RR <= rr <= MAX_RR):
                    continue

                data = {
                    "symbol": symbol,
                    "trade_type": trade_type,
                    "side": result["side"],
                    "entry": result["entry"],
                    "stop": result["stop"],
                    "take": result["take"],
                    "rr": rr,
                    "strength": result["strength"],
                    "reason": result["reason"]
                }
                signal_id = save_signal(data)

                emoji = SIGNAL_EMOJI.get(result["strength"], "⚪")
                text = f"""
{emoji} <b>{meta['name']} | {symbol}</b>

Направление: <b>{result['side']}</b>
Вход: <code>{result['entry']}</code>
Стоп: <code>{result['stop']}</code>
Тейк: <code>{result['take']}</code>
R:R = <b>1:{rr:.2f}</b>

{result['reason']}
"""
                if CHANNEL_ID:
                    await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
            except Exception as e:
                print(f"Ошибка {symbol}: {e}")
