import asyncio
from analyzer import analyze_coin
from database import save_signal
from config import MIN_RR, MAX_RR, TRADE_TYPES, SIGNAL_EMOJI
from telegram import Bot
from config import CHANNEL_ID

# Фиксированный список топ монет (чтобы не зависеть от бирж)
TOP_COINS_LIST = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
    "MATIC/USDT", "LTC/USDT", "ATOM/USDT", "UNI/USDT", "NEAR/USDT",
    "APT/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT", "PEPE/USDT",
    "SHIB/USDT", "TRX/USDT", "TON/USDT", "ICP/USDT", "FIL/USDT",
    "AAVE/USDT", "MKR/USDT", "INJ/USDT", "SEI/USDT", "TIA/USDT"
]

async def get_top_volume_coins():
    return TOP_COINS_LIST

async def scan_once(bot: Bot):
    coins = await get_top_volume_coins()
    print(f"Сканируем {len(coins)} монет...")

    for trade_type, meta in TRADE_TYPES.items():
        for symbol in coins:
            try:
                # Передаём минимальные данные, анализ делает Groq
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
                    "reason": result.get("reason", "")
                }
                
                save_signal(data)

                emoji = SIGNAL_EMOJI.get(result.get("strength", "medium"), "⚪")
                text = f"""
{emoji} <b>{meta['name']} | {symbol}</b>

Направление: <b>{result.get('side')}</b>
Вход: <code>{result.get('entry')}</code>
Стоп: <code>{result.get('stop')}</code>
Тейк: <code>{result.get('take')}</code>
R:R = <b>1:{rr:.2f}</b>

{result.get('reason')}
"""
                if CHANNEL_ID:
                    await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
                    
                # Небольшая пауза, чтобы не превысить лимиты Groq
                await asyncio.sleep(1.5)

            except Exception as e:
                print(f"Ошибка {symbol}: {e}")
