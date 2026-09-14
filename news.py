import feedparser
import aiohttp

async def get_crypto_news(limit=8):
    feeds = [
        "https://cryptopanic.com/news/rss/",
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/"
    ]
    news = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                news.append({
                    "title": entry.title,
                    "link": entry.link,
                    "source": feed.feed.get("title", "News")
                })
        except:
            continue
    return news[:limit]
