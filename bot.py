import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, CHANNEL_ID
from database import init_db, get_active_signals, get_recent_signals, get_stats
from scanner import scan_once
from stats_checker import check_open_signals
from news import get_crypto_news
from analyzer import analyze_coin

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("₿ Биткоин дня", callback_data="btc_day")],
        [InlineKeyboardButton("📊 Последние сигналы", callback_data="last_signals")],
        [InlineKeyboardButton("📈 Статистика", callback_data="stats")],
        [InlineKeyboardButton("📰 Новости", callback_data="news")],
        [InlineKeyboardButton("⚙️ Панель управления", callback_data="admin_panel")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в Crypto Signal Bot\n\nВыберите действие:",
        reply_markup=main_menu()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "btc_day":
        result = await analyze_coin("BTC/USDT", "4h", "Текущий анализ Bitcoin")
        text = f"₿ <b>Биткоин дня</b>\n\n{result.get('reason', 'Нет данных')}"
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "last_signals":
        signals = get_recent_signals(10)
        if not signals:
            await query.edit_message_text("Пока нет сигналов.")
            return
        status_map = {"win": "✅", "loss": "❌", "expired": "⏰", "active": "⏳"}
        text = "<b>Последние 10 сигналов:</b>\n\n"
        for s in signals:
            emoji = status_map.get(s[11], "⚪")
            text += f"{emoji} {s[1]} | {s[2]} | R:R 1:{s[7]:.1f}\n"
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "stats":
        st = get_stats()
        closed = st["win"] + st["loss"]
        winrate = round(st["win"] / closed * 100, 1) if closed > 0 else 0.0

        text = (
            f"📈 <b>Статистика сделок</b>\n\n"
            f"Всего сигналов: <b>{st['total']}</b>\n"
            f"✅ Успешных (TP): <b>{st['win']}</b>\n"
            f"❌ Убыточных (SL): <b>{st['loss']}</b>\n"
            f"⏰ Истекло: <b>{st['expired']}</b>\n"
            f"⏳ В ожидании: <b>{st['active']}</b>\n\n"
            f"Winrate (закрытые): <b>{winrate}%</b>\n"
            f"Средний R:R: <b>1:{st['avg_rr']}</b>\n"
        )

        if st["by_type"]:
            text += "\n<b>По типам:</b>\n"
            for ttype, data in st["by_type"].items():
                text += (
                    f"• {ttype}: {data['total']} сигналов, "
                    f"winrate {data['winrate']}%\n"
                )

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu())

    elif data == "news":
        news_list = await get_crypto_news()
        text = "<b>Последние новости:</b>\n\n"
        for n in news_list:
            text += f"• <a href='{n['link']}'>{n['title']}</a>\n"
        await query.edit_message_text(text, parse_mode="HTML", disable_web_page_preview=True)

    elif data == "admin_panel":
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("Доступ запрещён.")
            return
        status = "▶️ Активно" if config.SCANNING_ENABLED else "⏸ Остановлено"
        toggle_text = "⏸ Остановить сканирование" if config.SCANNING_ENABLED else "▶️ Возобновить сканирование"
        keyboard = [
            [InlineKeyboardButton(f"Сканер: {status}", callback_data="noop")],
            [InlineKeyboardButton(toggle_text, callback_data="toggle_scan")],
            [InlineKeyboardButton("🔄 Запустить сканер сейчас", callback_data="force_scan")],
            [InlineKeyboardButton("🔍 Проверить сделки", callback_data="check_trades")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")]
        ]
        await query.edit_message_text(
            "⚙️ Панель управления",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "toggle_scan":
        if user_id not in ADMIN_IDS:
            return
        config.SCANNING_ENABLED = not config.SCANNING_ENABLED
        status = "▶️ активно" if config.SCANNING_ENABLED else "⏸ остановлено"
        await query.answer(f"Сканирование {status}")
        # Обновить меню
        status_label = "▶️ Активно" if config.SCANNING_ENABLED else "⏸ Остановлено"
        toggle_text = "⏸ Остановить сканирование" if config.SCANNING_ENABLED else "▶️ Возобновить сканирование"
        keyboard = [
            [InlineKeyboardButton(f"Сканер: {status_label}", callback_data="noop")],
            [InlineKeyboardButton(toggle_text, callback_data="toggle_scan")],
            [InlineKeyboardButton("🔄 Запустить сканер сейчас", callback_data="force_scan")],
            [InlineKeyboardButton("🔍 Проверить сделки", callback_data="check_trades")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")]
        ]
        await query.edit_message_text(
            "⚙️ Панель управления",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "noop":
        await query.answer()

    elif data == "force_scan":
        if user_id not in ADMIN_IDS:
            return
        await query.edit_message_text("Сканер запущен...")
        await scan_once(context.bot)
        await query.edit_message_text("Сканирование завершено.", reply_markup=main_menu())

    elif data == "check_trades":
        if user_id not in ADMIN_IDS:
            return
        await query.edit_message_text("Проверяю открытые сделки...")
        await check_open_signals()
        await query.edit_message_text("Проверка завершена.", reply_markup=main_menu())

    elif data == "back_main":
        await query.edit_message_text(
            "Выберите действие:",
            reply_markup=main_menu()
        )


async def main():
    init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(scan_once, "interval", hours=1, args=[app.bot])
    scheduler.add_job(check_open_signals, "interval", minutes=30)
    scheduler.start()

    logger.info("Бот запускается...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
