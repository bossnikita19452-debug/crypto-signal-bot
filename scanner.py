import asyncio
import aiohttp
from datetime import datetime

import config
from analyzer import analyze_coin
from indicators import calculate_adx, calculate_atr
from database import (
    save_signal,
    has_active_signal,
    get_toxic_symbols,
)
from config import (
    MIN_RR, MAX_RR, TRADE_TYPES, SIGNAL_EMOJI, CHANNEL_ID,
    USE_GROUPS, NUM_GROUPS,
    ADX_MIN, ATR_MIN_PCT, ATR_MAX_PCT, MIN_STOP_PCT,
)
from telegram import Bot
from stats_checker import check_open_signals
from news import get_news_for_coin, get_fear_greed

COINS = {
    "BTC/USDT": "bitcoin", "ETH/USDT": "ethereum", "BNB/USDT": "binancecoin",
    "XRP/USDT": "ripple", "SOL/USDT": "solana", "TRX/USDT": "tron",
    "DOGE/USDT": "dogecoin", "ADA/USDT": "cardano", "AVAX/USDT": "avalanche-2",
    "LINK/USDT": "chainlink", "SUI/USDT": "sui", "TON/USDT": "the-open-network",
    "ARB/USDT": "arbitrum", "OP/USDT": "optimism", "APT/USDT": "aptos",
    "NEAR/USDT": "near", "ATOM/USDT": "cosmos", "DOT/USDT": "polkadot",
    "SEI/USDT": "sei-network", "INJ/USDT": "injective-protocol",
    "AAVE/USDT": "aave", "UNI/USDT": "uniswap", "LDO/USDT": "lido-dao",
    "CRV/USDT": "curve-dao-token", "PENDLE/USDT": "pendle",
    "JUP/USDT": "jupiter-exchange-solana", "PYTH/USDT": "pyth-network",
    "WIF/USDT": "dogwifcoin", "PEPE/USDT": "pepe", "SHIB/USDT": "shiba-inu",
    "HYPE/USDT": "hyperliquid", "ZEC/USDT": "zcash", "XMR/USDT": "monero",
    "FIL/USDT": "filecoin", "ICP/USDT": "internet-computer",
    "RNDR/USDT": "render-token", "FET/USDT": "fetch-ai",
    "TAO/USDT": "bittensor", "AKT/USDT": "akash-network",
    "AKE/USDT": "akedo", "ETC/USDT": "ethereum-classic",
    "XLM/USDT": "stellar", "ALGO/USDT": "algorand", "VET/USDT": "vechain",
    "HBAR/USDT": "hedera-hashgraph", "EGLD/USDT": "elrond-erd-2",
    "THETA/USDT": "theta-token", "FLOW/USDT": "flow", "MANA/USDT": "decentraland",
    "SAND/USDT": "the-sandbox", "AXS/USDT": "axie-infinity", "GALA/USDT": "gala",
    "IMX/USDT": "immutable-x", "GMT/USDT": "stepn", "APE/USDT": "apecoin",
    "CHZ/USDT": "chiliz", "1INCH/USDT": "1inch", "COMP/USDT": "compound-governance-token",
    "MKR/USDT": "maker", "SNX/USDT": "havven", "ZRX/USDT": "0x",
    "BAT/USDT": "basic-attention-token", "ENJ/USDT": "enjincoin",
    "YFI/USDT": "yearn-finance", "SUSHI/USDT": "sushi", "KSM/USDT": "kusama",
    "ZIL/USDT": "zilliqa", "ONE/USDT": "harmony", "IOTA/USDT": "iota", "NEO/USDT": "neo",
}


def _get_current_group() -> list:
    all_symbols = list(COINS.keys())
    if not USE_GROUPS or NUM_GROUPS <= 1:
        return all_symbols
    hour = datetime.utcnow().hour
    group_index = hour % NUM_GROUPS
    group_size = len(all_symbols) // NUM_GROUPS
    start = group_index * group_size
    if group_index == NUM_GROUPS - 1:
        return all_symbols[start:]
    return all_symbols[start:start + group_size]


async def get_prices(symbols: list):
    ids = ",".join(COINS[s] for s in symbols if s in COINS)
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

    symbols = _get_current_group()
    group_num = datetime.utcnow().hour % NUM_GROUPS if USE_GROUPS else 0
    print(f"=== Группа {group_num + 1}/{NUM_GROUPS}: {len(symbols)} монет ===")

    toxic = set(get_toxic_symbols())
    if toxic:
        print(f"⚠️ Токсичные монеты (пропуск): {', '.join(toxic)}")

    prices = await get_prices(symbols)
    meta = TRADE_TYPES["swing"]

    async with aiohttp.ClientSession() as session:
        fg = await get_fear_greed(session)
        fg_text = f"Fear & Greed: {fg.get('value', 50)} ({fg.get('classification', 'Neutral')})"

        for symbol in symbols:
            if not config.SCANNING_ENABLED:
                return
            if symbol in toxic:
                print(f"🚫 {symbol}: в токсичных — пропускаем")
                continue

            try:
                if has_active_signal(symbol):
                    print(f"⏳ {symbol}: уже есть активный сигнал")
                    continue

                gecko_id = COINS[symbol]
                current_price = prices.get(gecko_id, {}).get("usd")
                if not current_price:
                    continue

                news = await get_news_for_coin(session, symbol, limit=5)
                news_text = "\n".join(f"- {h}" for h in news) if news else "Новостей нет."

                market_data = (
                    f"Монета: {symbol}\n"
                    f"Текущая цена: ${current_price}\n"
                    f"Таймфрейм: {meta['tf']}\n"
                    f"{fg_text}\n"
                    f"Новости:\n{news_text}\n\n"
                    f"Ищи сетап для входа по рынку СЕЙЧАС."
                )

                result = await analyze_coin(symbol, market_data)

                if "error" in result:
                    err = str(result["error"])
                    if "429" in err or "rate" in err.lower():
                        await asyncio.sleep(10)
                    else:
                        print(f"Ошибка анализа {symbol}: {err}")
                    continue

                side = result.get("side", "NONE")
                if side == "NONE":
                    continue

                entry = current_price
                stop = result.get("stop", 0)
                take = result.get("take", 0)

                if not stop or not take:
                    continue

                risk = abs(entry - stop)
                reward = abs(take - entry)
                if risk <= 0:
                    continue
                rr = round(reward / risk, 2)
                if not (meta["min_rr"] <= rr <= meta["max_rr"]):
                    continue

                stop_pct = abs(entry - stop) / entry * 100
                if stop_pct < MIN_STOP_PCT:
                    continue

                leverage = round(100 / stop_pct) if stop_pct > 0 else 1

                data = {
                    "symbol": symbol,
                    "trade_type": "swing",
                    "side": side,
                    "entry": entry,
                    "stop": stop,
                    "take": take,
                    "rr": rr,
                    "strength": result.get("strength", "medium"),
                    "reason": result.get("reason", ""),
                }
                save_signal(data)

                emoji = SIGNAL_EMOJI.get(result.get("strength", "medium"), "⚪")
                text = (
                    f"{emoji} <b>{meta['name']} | {symbol}</b>\n\n"
                    f"Вход (сейчас): <code>${entry}</code>\n"
                    f"Направление: <b>{side}</b>\n"
                    f"Стоп: <code>{stop}</code>\n"
                    f"Тейк: <code>{take}</code>\n"
                    f"R:R = <b>1:{rr:.2f}</b>\n"
                    f"⚡ Плечо: <b>{leverage}x</b>\n"
                    f"📏 Стоп: <b>{stop_pct:.2f}%</b>\n\n"
                    f"{result.get('reason')}"
                )

                if CHANNEL_ID:
                    try:
                        await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
                    except Exception as e:
                        print(f"Ошибка отправки {symbol}: {e}")

                await asyncio.sleep(7)

            except Exception as e:
                print(f"Ошибка {symbol}: {e}")

    await check_open_signals(chat_id=CHANNEL_ID)
