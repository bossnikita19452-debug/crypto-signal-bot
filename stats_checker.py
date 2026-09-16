from datetime import datetime, timedelta
import aiohttp

from database import get_active_signals, update_signal_status


# Срок жизни сделки до пометки "expired"
EXPIRY = {
    "scalp": timedelta(hours=2),
    "swing": timedelta(days=4),
    "longterm": timedelta(days=35),
}

COIN_IDS = {
    "BTC/USDT": "bitcoin", "ETH/USDT": "ethereum", "SOL/USDT": "solana",
    "XRP/USDT": "ripple", "AVAX/USDT": "avalanche-2", "AAVE/USDT": "aave",
    "ARB/USDT": "arbitrum", "TON/USDT": "the-open-network", "SUI/USDT": "sui",
    "XMR/USDT": "monero", "ZEC/USDT": "zcash", "PEPE/USDT": "pepe",
    "INJ/USDT": "injective-protocol", "HYPE/USDT": "hyperliquid",
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
        # Индексы соответствуют структуре таблицы signals:
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
