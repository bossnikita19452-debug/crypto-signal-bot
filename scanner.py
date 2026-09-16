import asyncio
import aiohttp
from analyzer import analyze_coin
from database import save_signal
from config import MIN_RR, MAX_RR, TRADE_TYPES, SIGNAL_EMOJI, CHANNEL_ID
from telegram import Bot
from stats_checker import check_open_signals

COINS = {
    "BTC/USDT": "bitcoin",
    "ETH/USDT": "ethereum",
    "SOL/USDT": "solana",
    "XRP/USDT": "ripple",
    "AVAX/USDT": "avalanche-2",
    "AAVE/USDT": "aave",
    "ARB/USDT": "arbitrum",
    "TON/USDT": "the-open-network",
    "SUI/USDT": "sui",
    "XMR/USDT": "monero",
    "ZEC/USDT": "zcash",
    "PEPE/USDT": "pepe",
    "INJ/USDT": "injective-protocol",
    "HYPE/USDT": "hyperliquid",
    "AKE/USDT": "akedo",
}


async def get_prices():
    ids = ",".join(COINS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        print(f"Ошибка получения цен: {e}")
    return {}


async def scan_once(bot: Bot):
    prices = await get_prices()
    print(f"Сканируем {len(COINS)} монет (тренд, 4ч)...")

    meta = TRADE_TYPES["swing"]

    for symbol, gecko_id in COINS.items():
        try:
            price_data = prices.get(gecko_id, {})
            current_price = price_data.get("usd")
            if not current_price:
                continue

            market_data = (
                f"Монета: {symbol}\n"
                f"Текущая цена: ${current_price}\n"
                f"Таймфрейм: {meta['tf']}\n"
                f"Ищи трендовый сетап с откатом для среднесрочной торговли."
            )

            result = await analyze_coin(symbol, meta["tf"], market_data)

            if "error" in result:
                print(f"Ошибка анализа {symbol}: {result['error']}")
                continue

            side = result.get("side", "NONE")
            if side == "NONE":
                continue

            rr = float(result.get("rr", 0))
            if not (meta["min_rr"] <= rr <= meta["max_rr"]):
                continue

            data = {
                "symbol": symbol,
                "trade_type": "swing",
                "side": side,
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
                f"Текущая цена: <code>${current_price}</code>\n"
                f"Направление: <b>{side}</b>\n"
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
                    print(f"Ошибка отправки {symbol}: {e}")

            await asyncio.sleep(2)

        except Exception as e:
            print(f"Ошибка {symbol}: {e}")

    await check_open_signals()

