from datetime import datetime, timedelta
import aiohttp

from database import (
    get_active_signals,
    update_signal_status,
    mark_triggered,
)

EXPIRY = {
    "scalp": timedelta(hours=2),
    "swing": timedelta(days=4),
    "longterm": timedelta(days=35),
}

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
    "ETC/USDT": "ethereum-classic",
    "XLM/USDT": "stellar",
    "ALGO/USDT": "algorand",
    "VET/USDT": "vechain",
    "HBAR/USDT": "hedera-hashgraph",
    "EGLD/USDT": "elrond-erd-2",
    "THETA/USDT": "theta-token",
    "FLOW/USDT": "flow",
    "MANA/USDT": "decentraland",
    "SAND/USDT": "the-sandbox",
    "AXS/USDT": "axie-infinity",
    "GALA/USDT": "gala",
    "IMX/USDT": "immutable-x",
    "GMT/USDT": "stepn",
    "APE/USDT": "apecoin",
    "CHZ/USDT": "chiliz",
    "1INCH/USDT": "1inch",
    "COMP/USDT": "compound-governance-token",
    "MKR/USDT": "maker",
    "SNX/USDT": "havven",
    "ZRX/USDT": "0x",
    "BAT/USDT": "basic-attention-token",
    "ENJ/USDT": "enjincoin",
    "YFI/USDT": "yearn-finance",
    "SUSHI/USDT": "sushi",
    "KSM/USDT": "kusama",
    "ZIL/USDT": "zilliqa",
    "ONE/USDT": "harmony",
    "IOTA/USDT": "iota",
    "NEO/USDT": "neo",
}

_bot = None


def set_bot(bot):
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
    if _bot is None or not chat_id:
        return
    try:
        await _bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка уведомления: {e}")


async def check_open_signals(chat_id=None):
    signals = get_active_signals(limit=100)
    if not signals:
        print("Нет активных сделок для проверки")
        return

    prices = await _get_prices()
    now = datetime.utcnow()

    for s in signals:
        # Индексы: 0=id, 1=symbol, 2=trade_type, 3=side, 4=entry, 5=stop, 6=take,
        # 7=rr, 8=strength, 9=reason, 10=created_at, 11=status,
        # 12=triggered, 13=result_price, 14=closed_at
        sig_id = s[0]
        symbol = s[1]
        trade_type = s[2]
        side = s[3]
        entry = s[4]
        stop = s[5]
        take = s[6]
        rr = s[7]
        created_at = datetime.fromisoformat(s[10])
        triggered = s[12] if len(s) > 12 else 0

        gecko_id = COIN_IDS.get(symbol)
        if not gecko_id:
            continue

        current = prices.get(gecko_id, {}).get("usd")
        if not current:
            continue

        # ─── Проверяем, активирован ли вход ─────────────────────
        # Для LONG: вход активирован, если цена опустилась до entry (или ниже)
        # Для SHORT: вход активирован, если цена поднялась до entry (или выше)
        if not triggered:
            if side == "LONG" and current <= entry:
                mark_triggered(sig_id)
                triggered = 1
                print(f"📥 {symbol}: вход активирован (${current} <= ${entry})")
            elif side == "SHORT" and current >= entry:
                mark_triggered(sig_id)
                triggered = 1
                print(f"📥 {symbol}: вход активирован (${current} >= ${entry})")

        # ─── Проверяем TP/SL только если вход активирован ───────
        if triggered:
            if side == "LONG":
                if current >= take:
                    update_signal_status(sig_id, "win", current)
                    profit_pct = (current - entry) / entry * 100
                    msg = (
                        f"✅ <b>ТЕЙК ПРОФИТ</b>\n\n"
                        f"Монета: <b>{symbol}</b>\n"
                        f"Направление: LONG\n"
                        f"Вход: <code>{entry}</code>\n"
                        f"Тейк: <code>{take}</code>\n"
                        f"Текущая: <code>{current}</code>\n"
                        f"Профит: <b>+{profit_pct:.2f}%</b>\n"
                        f"R:R: 1:{rr:.2f}"
                    )
                    await _notify(chat_id, msg)
                    continue
                if current <= stop:
                    update_signal_status(sig_id, "loss", current)
                    loss_pct = (current - entry) / entry * 100
                    msg = (
                        f"❌ <b>СТОП ЛОСС</b>\n\n"
                        f"Монета: <b>{symbol}</b>\n"
                        f"Направление: LONG\n"
                        f"Вход: <code>{entry}</code>\n"
                        f"Стоп: <code>{stop}</code>\n"
                        f"Текущая: <code>{current}</code>\n"
                        f"Убыток: <b>{loss_pct:.2f}%</b>"
                    )
                    await _notify(chat_id, msg)
                    continue

        # ─── Проверка срока ─────────────────────────────────────
        expiry = EXPIRY.get(trade_type, timedelta(days=4))
        if now - created_at > expiry:
            if triggered:
                # Вход был, но не дошли ни до TP, ни до SL — expired
                update_signal_status(sig_id, "expired", current)
                await _notify(
                    chat_id,
                    f"⏰ <b>СДЕЛКА ИСТЕКЛА</b>\n\n"
                    f"Монета: <b>{symbol}</b>\n"
                    f"Вход: <code>{entry}</code>\n"
                    f"Текущая: <code>{current}</code>\n"
                    f"Прошло больше {expiry.days} дн."
                )
            else:
                # Вход так и не активировался — отдельный статус
                update_signal_status(sig_id, "not_triggered", current)
                await _notify(
                    chat_id,
                    f"⚪️ <b>ВХОД НЕ АКТИВИРОВАН</b>\n\n"
                    f"Монета: <b>{symbol}</b>\n"
                    f"Вход: <code>{entry}</code>\n"
                    f"Текущая: <code>{current}</code>\n"
                    f"Цена не дошла до входа за {expiry.days} дн."
                )
