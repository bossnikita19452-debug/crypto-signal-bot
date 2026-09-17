import aiohttp


NEWS_BASE = "https://cryptocurrency.cv"
FEAR_GREED_URL = "https://api.alternative.me/fng/"


async def get_news_for_coin(session: aiohttp.ClientSession, symbol: str, limit: int = 5) -> list:
    """Получить заголовки новостей по монете."""
    coin = symbol.split("-")[0].upper()
    if coin in ("USDT", "USDC", "BUSD", "DAI"):
        return []

    try:
        url = f"{NEWS_BASE}/api/news"
        params = {"q": coin, "limit": limit}
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
    except Exception:
        return []

    headlines = []
    articles = data.get("articles", data.get("data", []))
    for item in articles[:limit]:
        title = item.get("title")
        if title:
            headlines.append(title)
    return headlines


async def get_crypto_news(limit: int = 5) -> list:
    """Общие новости крипторынка (для кнопки «Новости» в боте)."""
    url = f"{NEWS_BASE}/api/news"
    params = {"limit": limit}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
    except Exception:
        return []

    result = []
    articles = data.get("articles", data.get("data", []))
    for item in articles[:limit]:
        title = item.get("title")
        if title:
            result.append({
                "title": title,
                "link": item.get("url", item.get("link", "")),
            })
    return result


async def get_fear_greed(session: aiohttp.ClientSession) -> dict:
    """Fear & Greed Index."""
    try:
        async with session.get(FEAR_GREED_URL, timeout=10) as resp:
            if resp.status != 200:
                return {}
            data = await resp.json()
    except Exception:
        return {}

    if not data.get("data"):
        return {}
    item = data["data"][0]
    return {
        "value": int(item.get("value", 50)),
        "classification": item.get("value_classification", "Neutral"),
    }
