from datetime import datetime, timedelta
import aiohttp

from database import get_active_signals, update_signal_status


# Срок жизни сделки до пометки "expired"
EXPIRY = {
    "scalp": timedelta(hours=2),
    "swing": timedelta(days=4),
    "longterm": timedelta(days=35),
}


# Расширенный список ID CoinGecko (синхронизирован с scanner.py)
COIN_IDS = {
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


async def _get_prices():
    ids = ",".join(set(COIN_IDS.values()))
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        print(f"Ошибка цен: {e}")
    return {}


async def check_open_signals():
    """Проверить все активные сделки и обновить статусы."""
    signals = get_active_signals(limit=100)
    if not signals:
        print("Нет активных сделок для проверки")
        return

    prices = await _get_prices()
    now = datetime.utcnow()

    for s in signals:
        # Индексы таблицы signals:
        # 0=id, 1=symbol, 2=trade_type, 3=side, 4=entry, 5=stop, 6=take,
        # 7=rr, 8=strength, 9=reason, 10=created_at, 11=status
        sig_id = s[0]
        symbol = s[1]
        trade_type = s[2]
        entry = s[4]
        stop = s[5]
        take = s[6]
        created_at = datetime.fromisoformat(s[10])

        gecko_id = COIN_IDS.get(symbol)
        if not gecko_id:
            continue

        current = prices.get(gecko_id, {}).get("usd")
        if not current:
            continue

        # Проверка TP
        if current >= take:
            update_signal_status(sig_id, "win", current)
            print(f"✅ {symbol} закрыт по TP: {current} (вход {entry})")
            continue

        # Проверка SL
        if current <= stop:
            update_signal_status(sig_id, "loss", current)
            print(f"❌ {symbol} закрыт по SL: {current} (вход {entry})")
            continue

        # Проверка срока
        expiry = EXPIRY.get(trade_type, timedelta(days=4))
        if now - created_at > expiry:
            update_signal_status(sig_id, "expired", current)
            print(f"⏰ {symbol} истёк: {current} (вход {entry})")
