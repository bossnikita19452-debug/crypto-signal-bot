from datetime import datetime, timedelta
import aiohttp

from database import get_active_signals, update_signal_status

# Срок жизни сделки до пометки "expired"
EXPIRY = {
    "scalp": timedelta(hours=2),
    "swing": timedelta(days=4),
    "longterm": timedelta(days=35),
}

# ID CoinGecko для монет
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

# Глобальная ссылка на бота (устанавливается извне)
_bot = None

def set_bot(bot):
    """Установить экземпляр бота для отправки уведомлений."""
    global _bot
    _bot = bot


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


async def _notify(chat_id, text: str):
    """Отправить уведомление в Telegram."""
    if _bot is None or not chat_id:
        return
    try:
        await _bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка уведомления: {e}")


async def check_open_signals(chat_id=None):
    """
    Проверить активные сделки и обновить статусы.
    chat_id — куда отправлять уведомления (если None — не отправлять).
    """
    signals = get_active_signals(limit=100)
    if not signals:
        print("Нет активных сделок для проверки")
        return

    prices = await _get_prices()
    now = datetime.utcnow()

    for s in signals:
        # Индексы: 0=id, 1=symbol, 2=trade_type, 3=side, 4=entry, 5=stop, 6=take,
        # 7=rr, 8=strength, 9=reason, 10=created_at, 11=status
        sig_id = s[0]
        symbol = s[1]
        trade_type = s[2]
        side = s[3]
        entry = s[4]
        stop = s[5]
        take = s[6]
        rr = s[7]
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
            profit_pct = (current - entry) / entry * 100
            msg = (
                f"✅ <b>ТЕЙК ПРОФИТ СРАБОТАЛ</b>\n\n"
                f"Монета: <b>{symbol}</b>\n"
                f"Направление: {side}\n"
                f"Вход: <code>{entry}</code>\n"
                f"Тейк: <code>{take}</code>\n"
                f"Текущая цена: <code>{current}</code>\n"
                f"Профит: <b>+{profit_pct:.2f}%</b>\n"
                f"R:R: 1:{rr:.2f}"
            )
            print(f"✅ {symbol} закрыт по TP: {current}")
            await _notify(chat_id, msg)
            continue

        # Проверка SL
        if current <= stop:
            update_signal_status(sig_id, "loss", current)
            loss_pct = (current - entry) / entry * 100
            msg = (
                f"❌ <b>СТОП ЛОСС СРАБОТАЛ</b>\n\n"
                f"Монета: <b>{symbol}</b>\n"
                f"Направление: {side}\n"
                f"Вход: <code>{entry}</code>\n"
                f"Стоп: <code>{stop}</code>\n"
                f"Текущая цена: <code>{current}</code>\n"
                f"Убыток: <b>{loss_pct:.2f}%</b>"
            )
            print(f"❌ {symbol} закрыт по SL: {current}")
            await _notify(chat_id, msg)
            continue

        # Проверка срока
        expiry = EXPIRY.get(trade_type, timedelta(days=4))
        if now - created_at > expiry:
            update_signal_status(sig_id, "expired", current)
            msg = (
                f"⏰ <b>СДЕЛКА ИСТЕКЛА</b>\n\n"
                f"Монета: <b>{symbol}</b>\n"
                f"Направление: {side}\n"
                f"Вход: <code>{entry}</code>\n"
                f"Текущая цена: <code>{current}</code>\n"
                f"Прошло больше {expiry.days} дн."
            )
            print(f"⏰ {symbol} истёк: {current}")
            await _notify(chat_id, msg)
