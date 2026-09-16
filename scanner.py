import asyncio
import aiohttp
import config
from analyzer import analyze_coin
from database import save_signal, has_active_signal
from config import MIN_RR, MAX_RR, TRADE_TYPES, SIGNAL_EMOJI, CHANNEL_ID
from telegram import Bot
from stats_checker import check_open_signals

COINS = {
    "BTC/USDT": "bitcoin",
    "ETH/USDT": "ethereum",
    "BNB/USDT": "binancecoin",
    "XRP/USDT": "ripple",
    "SOL/USDT": "solana",
    "TRX/USDT": "tron",
    "DOGE/USDT": "dogecoin",
    "ADA/USDT": "cardano",
    "AVAX/USDT": "avalanche-2",
    "LINK/USDT": "chainlink",
    "SUI/USDT": "sui",
    "TON/USDT": "the-open-network",
    "ARB/USDT": "arbitrum",
    "OP/USDT": "optimism",
    "APT/USDT": "aptos",
    "NEAR/USDT": "near",
    "ATOM/USDT": "cosmos",
    "DOT/USDT": "polkadot",
    "SEI/USDT": "sei-network",
    "INJ/USDT": "injective-protocol",
    "AAVE/USDT": "aave",
    "UNI/USDT": "uniswap",
    "LDO/USDT": "lido-dao",
    "CRV/USDT": "curve-dao-token",
    "PENDLE/USDT": "pendle",
    "JUP/USDT": "jupiter-exchange-solana",
    "PYTH/USDT": "pyth-network",
    "WIF/USDT": "dogwifcoin",
    "PEPE/USDT": "pepe",
    "SHIB/USDT": "shiba-inu",
    "HYPE/USDT": "hyperliquid",
    "ZEC/USDT": "zcash",
    "XMR/USDT": "monero",
    "FIL/USDT": "filecoin",
    "ICP/USDT": "internet-computer",
    "RNDR/USDT": "render-token",
    "FET/USDT": "fetch-ai",
    "TAO/USDT": "bittensor",
    "AKT/USDT": "akash-network",
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
    if not config.SCANNING_ENABLED:
        print("⏸ Сканирование остановлено пользователем")
        return

    prices = await get_prices()
    print(f"Сканируем {len(COINS)} монет (тренд, 4ч)...")

    meta = TRADE_TYPES["swing"]

    for symbol, gecko_id in COINS.items():
        if not config.SCANNING_ENABLED:
            print("⏸ Сканирование остановлено (в процессе)")
            return

        try:
            # Пропускаем монеты, по которым уже есть активный сигнал
            if has_active_signal(symbol):
                print(f"⏳ {symbol}: уже есть активный сигнал — пропускаем")
                continue

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
                err = str(result["error"])
                if "429" in err or "rate" in err.lower():
                    print(f"⚠️ {symbol}: лимит Groq, пауза 10 сек")
                    await asyncio.sleep(10)
                else:
                    print(f"Ошибка анализа {symbol}: {err}")
                continue

            side = result.get("side", "NONE")
            if side == "NONE":
                continue

            rr = float(result.get("rr", 0))
            if not (meta["min_rr"] <= rr <= meta["max_rr"]):
                continue

            entry = result.get("entry", 0)
            stop = result.get("stop", 0)

            if entry and stop and entry > stop:
                stop_pct = (entry - stop) / entry * 100
                leverage = round(100 / stop_pct) if stop_pct > 0 else 1
            else:
                leverage = 1

            data = {
                "symbol": symbol,
                "trade_type": "swing",
                "side": side,
                "entry": entry,
                "stop": stop,
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
                f"Вход: <code>{entry}</code>\n"
                f"Стоп: <code>{stop}</code>\n"
                f"Тейк: <code>{result.get('take')}</code>\n"
                f"R:R = <b>1:{rr:.2f}</b>\n"
                f"⚡ Плечо: <b>{leverage}x</b> (стоп = 100% маржи)\n\n"
                f"{result.get('reason')}"
            )

            if CHANNEL_ID:
                try:
                    await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
                except Exception as e:
                    print(f"Ошибка отправки {symbol}: {e}")

            await asyncio.sleep(5)

        except Exception as e:
            print(f"Ошибка {symbol}: {e}")

    await check_open_signals(chat_id=CHANNEL_ID)

