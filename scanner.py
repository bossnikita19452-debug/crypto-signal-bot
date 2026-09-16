import asyncio
import aiohttp
from analyzer import analyze_coin
from database import save_signal
from config import MIN_RR, MAX_RR, TRADE_TYPES, SIGNAL_EMOJI
from telegram import Bot
from config import CHANNEL_ID

# Список монет + их ID на CoinGecko
COINS = {
    "BTC/USDT": "bitcoin",
    "ETH/USDT": "ethereum",
    "SOL/USDT": "solana",
    "BNB/USDT": "binancecoin",
    "XRP/USDT": "ripple",
    "DOGE/USDT": "dogecoin",
    "ADA/USDT": "cardano",
    "AVAX/USDT": "avalanche-2",
    "DOT/USDT": "polkadot",
    "LINK/USDT": "chainlink",
    "TON/USDT": "the-open-network",
    "TRX/USDT": "tron",
    "NEAR/USDT": "near",
    "APT/USDT": "aptos",
    "SUI/USDT": "sui"
}

async def get_prices():
    """Получаем актуальные цены с CoinGecko"""
    ids = ",".join(COINS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
            
