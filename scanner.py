import asyncio
from analyzer import analyze_coin
from database import save_signal
from config import MIN_RR, MAX_RR, TRADE_TYPES, SIGNAL_EMOJI
from telegram import Bot
from config import CHANNEL_ID

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

    trade_types_to_scan = {
        "scalp": TRADE_TYPES["scalp"]
    }

    for trade_type, meta in trade_types_to_scan.items():
        for symbol in coins:
            try:
                market_data = f"Монета: {symbol}. Таймфрейм: {meta['tf']}. Сделай технический анализ."
                
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
                
                text = (
                    f"{emoji} <b>{meta['name']} | {symbol}</b>\n\n"
                    f"Направление: <b>{result.get('side')}</b>\n"
                    f"Вход: <code>{result.get('entry')}</code>\n"
                    f"Стоп: <code>{result.get('stop')}</code>\n"
                    f"Тейк: <code>{result.get('take')}</code>\n"
                    f"R:R = <b>1:{rr:.2f}</b>\n\n"
                    f"{result.get('reason')}"
                )

                if CHANNEL_ID:
                    try:
                        await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
                    except Exception as e:
                        print(f"Ошибка отправки в канал {symbol}: {e}")
                    
                await asyncio.sleep(6)

            except Exception as e:
                print(f"Ошибка {symbol}: {e}")
