import asyncio
import aiohttp
from datetime import datetime

import config
from analyzer import analyze_coin
from indicators import calculate_adx, calculate_atr, calculate_ema
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

BYBIT_KLINE = "https://api.bybit.com/v5/market/kline"

# Расширенный список (до 150 монет)
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
    "ZIL/USDT": "zilliqa", "ONE/USDT": "harmony", "IOTA/USDT": "iota",
    "NEO/USDT": "neo", "WAVES/USDT": "waves", "QTUM/USDT": "qtum",
    "LSK/USDT": "lisk", "DASH/USDT": "dash", "ZEN/USDT": "horizen",
    "STORJ/USDT": "storj", "ANKR/USDT": "ankr", "CVC/USDT": "civic",
    "REN/USDT": "ren", "OCEAN/USDT": "ocean-protocol", "BAND/USDT": "band-protocol",
    "NMR/USDT": "numeraire", "KEEP/USDT": "keep-network", "BAL/USDT": "balancer",
    "RLC/USDT": "iexec-rlc", "KNC/USDT": "kyber-network-crystal",
    "MLN/USDT": "enzyme", "REP/USDT": "augur", "DNT/USDT": "district0x",
    "MANA/USDT": "decentraland", "LOOM/USDT": "loom-network",
    "MATIC/USDT": "matic-network", "FTM/USDT": "fantom", "S/USDT": "sonic-3",
    "CELO/USDT": "celo", "ROSE/USDT": "oasis-network", "KAVA/USDT": "kava",
    "BAND/USDT": "band-protocol", "CTSI/USDT": "cartesi", "SKL/USDT": "skale",
    "GRT/USDT": "the-graph", "DYDX/USDT": "dydx-chain", "ENS/USDT": "ethereum-name-service",
    "LRC/USDT": "loopring", "IMX/USDT": "immutable-x", "GODS/USDT": "gods-unchained",
    "ILV/USDT": "illuvium", "MAGIC/USDT": "magic", "PRIME/USDT": "echelon-prime",
    "PIXEL/USDT": "pixels", "PORTAL/USDT": "portal", "AI/USDT": "sleepless-ai",
    "XAI/USDT": "xai-blockchain", "ALT/USDT": "altlayer", "MANTA/USDT": "manta-network",
    "DYM/USDT": "dymension", "STRK/USDT": "starknet", "ZK/USDT": "zksync",
    "BLAST/USDT": "blast", "W/USDT": "wormhole", "OMNI/USDT": "omni-network",
    "REZ/USDT": "renzo", "ETHFI/USDT": "ether-fi", "EIGEN/USDT": "eigenlayer",
    "ZRO/USDT": "layerzero", "BANANA/USDT": "banana-gun", "DOGS/USDT": "dogs",
    "HMSTR/USDT": "hamster-kombat", "CATI/USDT": "catizen", "NEIRO/USDT": "neiro-3",
    "TURBO/USDT": "turbo", "MOG/USDT": "mog-coin", "POPCAT/USDT": "popcat",
    "BRETT/USDT": "based-brett", "TIA/USDT": "celestia", "DYM/USDT": "dymension",
    "SAGA/USDT": "saga-2", "OM/USDT": "mantra-dao", "ONDO/USDT": "ondo-finance",
    "PENDLE/USDT": "pendle", "AEVO/USDT": "aevo-exchange",
    "ETHFI/USDT": "ether-fi", "ENA/USDT": "ethena", "W/USDT": "wormhole",
    "JTO/USDT": "jito", "JUP/USDT": "jupiter-exchange-solana",
    "PYTH/USDT": "pyth-network", "TNSR/USDT": "tensor", "DRIFT/USDT": "drift-protocol",
    "WIF/USDT": "dogwifcoin", "BONK/USDT": "bonk", "MEW/USDT": "cat-in-a-dogs-world",
    "BOME/USDT": "book-of-meme", "SLERF/USDT": "slerf", "MYRO/USDT": "myro",
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


async def pre_filter(session: aiohttp.ClientSession, symbol: str) -> bool:
    """
    Предварительный технический фильтр через Bybit.
    Возвращает True, если монета прошла фильтр и стоит отправлять в ИИ.
    """
    bybit_symbol = symbol.replace("-", "").upper()

    try:
        params = {
            "category": "linear",
            "symbol": bybit_symbol,
            "interval": "240",
            "limit": 250,
        }
        async with session.get(BYBIT_KLINE, params=params, timeout=10) as resp:
            if resp.status != 200:
                return False
            data = await resp.json()
    except Exception:
        return False

    if data.get("retCode") != 0:
        return False

    rows = data.get("result", {}).get("list", [])
    if not rows or len(rows) < 200:
        return False

    # Bybit возвращает свечи в обратном порядке: [startTime, open, high, low, close, volume, turnover]
    # Разворачиваем в хронологический порядок
    rows = list(reversed(rows))

    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume", "turnover"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()

    if len(df) < 200:
        return False

    close = df["close"].iloc[-1]
    ema200 = calculate_ema(df, 200).iloc[-1]
    adx = calculate_adx(df, 14).iloc[-1]
    atr = calculate_atr(df, 14).iloc[-1]

    if pd.isna(ema200) or pd.isna(adx) or pd.isna(atr):
        return False

    atr_pct = atr / close * 100

    # Фильтры: тренд, сила тренда, волатильность
    trend_ok = close > ema200 * 0.98  # допуск 2%
    adx_ok = adx >= ADX_MIN
    atr_ok = ATR_MIN_PCT <= atr_pct <= ATR_MAX_PCT

    return trend_ok and adx_ok and atr_ok


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
        print(f"😱 {fg_text}")

        passed_filter = 0
        sent_to_ai = 0

        for symbol in symbols:
            if not config.SCANNING_ENABLED:
                return
            if symbol in toxic:
                print(f"🚫 {symbol}: токсичная")
                continue

            try:
                if has_active_signal(symbol):
                    print(f"⏳ {symbol}: уже активный сигнал")
                    continue

                gecko_id = COINS[symbol]
                current_price = prices.get(gecko_id, {}).get("usd")
                if not current_price:
                    print(f"❓ {symbol}: нет цены")
                    continue

                # ─── Предварительный технический фильтр ───────────
                passed = await pre_filter(session, symbol)
                if not passed:
                    continue  # тихо пропускаем, чтобы не засорять лог

                passed_filter += 1
                print(f"✅ {symbol}: прошёл фильтр (цена ${current_price})")

                # ─── Отправка в ИИ ────────────────────────────────
                print(f"🤖 {symbol}: отправляю в ИИ...")
                sent_to_ai += 1

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
                    print(f"⚠️ {symbol}: ошибка ИИ — {result['error']}")
                    err = str(result["error"])
                    if "429" in err or "rate" in err.lower():
                        await asyncio.sleep(10)
                    continue

                side = result.get("side", "NONE")
                if side == "NONE":
                    print(f"➡️ {symbol}: ИИ сказал NONE")
                    continue

                entry = current_price
                stop = result.get("stop", 0)
                take = result.get("take", 0)

                if not stop or not take:
                    print(f"⚠️ {symbol}: нет stop/take от ИИ")
                    continue

                risk = abs(entry - stop)
                reward = abs(take - entry)
                if risk <= 0:
                    continue
                rr = round(reward / risk, 2)
                if not (meta["min_rr"] <= rr <= meta["max_rr"]):
                    print(f"⛔ {symbol}: RR {rr} вне [{meta['min_rr']}, {meta['max_rr']}]")
                    continue

                stop_pct = abs(entry - stop) / entry * 100
                if stop_pct < MIN_STOP_PCT:
                    print(f"⛔ {symbol}: стоп {stop_pct:.2f}% < {MIN_STOP_PCT}%")
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
                        print(f"✅ {symbol}: сигнал отправлен!")
                    except Exception as e:
                        print(f"Ошибка отправки {symbol}: {e}")

                await asyncio.sleep(7)

            except Exception as e:
                print(f"Ошибка {symbol}: {e}")

        print(f"=== ИТОГО: прошло фильтр {passed_filter}, отправлено в ИИ {sent_to_ai} ===")

    await check_open_signals(chat_id=CHANNEL_ID)
