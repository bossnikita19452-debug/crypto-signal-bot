from datetime import datetime, timedelta
import aiohttp

from database import (
    get_active_signals,
    update_signal_status,
    mark_triggered,
    register_loss,
    register_win,
)

EXPIRY = {
    "scalp": timedelta(hours=2),
    "swing": timedelta(days=4),
    "longterm": timedelta(days=35),
}

COIN_IDS = {
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
        return

    prices = await _get_prices()
    now = datetime.utcnow()

    for s in signals:
        # 0=id, 1=symbol, 2=trade_type, 3=side, 4=entry, 5=stop, 6=take,
        # 7=rr, 8=strength, 9=reason, 10=created_at, 11=status,
        # 12=triggered, 13=result_price, 14=closed_at
        sig_id, symbol, trade_type, side = s[0], s[1], s[2], s[3]
        entry, stop, take, rr = s[4], s[5], s[6], s[7]
        created_at = datetime.fromisoformat(s[10])
        triggered = s[12] if len(s) > 12 else 0

        gecko_id = COIN_IDS.get(symbol)
        if not gecko_id:
            continue
        current = prices.get(gecko_id, {}).get("usd")
        if not current:
            continue

        # Активация входа
        if not triggered:
            if side == "LONG" and current <= entry:
                mark_triggered(sig_id)
                triggered = 1
            elif side == "SHORT" and current >= entry:
                mark_triggered(sig_id)
                triggered = 1

        if triggered:
            if side == "LONG":
                if current >= take:
                    update_signal_status(sig_id, "win", current)
                    register_win(symbol)
                    await _notify(chat_id, f"✅ <b>ТЕЙК ПРОФИТ</b>\n\n{symbol} | +{(current-entry)/entry*100:.2f}%")
                    continue
                if current <= stop:
                    update_signal_status(sig_id, "loss", current)
                    register_loss(symbol)
                    await _notify(chat_id, f"❌ <b>СТОП ЛОСС</b>\n\n{symbol} | {(current-entry)/entry*100:.2f}%")
                    continue

        expiry = EXPIRY.get(trade_type, timedelta(days=4))
        if now - created_at > expiry:
            if triggered:
                update_signal_status(sig_id, "expired", current)
            else:
                update_signal_status(sig_id, "not_triggered", current)
