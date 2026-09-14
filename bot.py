import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, CHANNEL_ID
from database import init_db, get_active_signals
from scanner import scan_once
from news import get_crypto_news
from analyzer import analyze_coin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("₿ Биткоин дня", callback_data="btc_day")],
        [InlineKeyboardButton("📊 Последние сигналы", callback_data="last_signals")],
        [InlineKeyboardButton("📰 Новости", callback_data="news")],
        [InlineKeyboardButton("⚙️ Панель управления", callback_data="admin_panel")]
    ]
    await update.message.reply_text(
        "Добро пожаловать в Crypto Signal Bot\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "btc_day":
        result = analyze_coin("BTC/USDT", "4h", "Анализ текущего дня по BTC")
        text = f"₿ <b>Биткоин дня</b>\n\n{result.get('reason', 'Нет данных')}"
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "last_signals":
        signals = get_active_signals(10)
        if not signals:
            await query.edit_message_text("Пока нет активных сигналов.")
            return
        text = "<b>Последние сигналы:</b>\n\n"
        for s in signals:
            text += f"• {s[1]} | {s[3]} | R:R 1:{s[7]:.1f}\n"
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "news":
        news = await get_crypto_news()
        text = "<b>Последние новости:</b>\n\n"
        for n in news:
            text += f"• <a href='{n['link']}'>{n['title']}</a>\n"
        await query.edit_message_text(text, parse_mode="HTML", disable_web_page_preview=True)

    elif data == "admin_panel":
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("Доступ запрещён.")
            return
        keyboard = [
            [InlineKeyboardButton("🔄 Запустить сканер сейчас", callback_data="force_scan")],
            [InlineKeyboardButton("📈 Статистика", callback_data="stats")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")]
        ]
        await query.edit_message_text("⚙️ Панель управления", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "force_scan":
        if user_id not in ADMIN_IDS:
            return
        await query.edit_message_text("Сканер запущен...")
        await scan_once(context.bot)
        await query.edit_message_text("Сканирование завершено.")

async def main():
    init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Сканер каждые 15 минут
    scheduler.add_job(scan_once, "interval", minutes=15, args=[app.bot])
    scheduler.start()

    print("Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
