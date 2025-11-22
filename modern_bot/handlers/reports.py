from telegram import Update
from telegram.ext import CallbackContext
from modern_bot.handlers.common import safe_reply, send_document_from_path
from modern_bot.handlers.admin import is_admin
from modern_bot.services.excel import read_excel_data, create_excel_snapshot
from modern_bot.services.archive import get_archive_paths, create_archive_zip
from modern_bot.utils.validators import get_month_bounds, match_region_name, parse_date_str

async def history_handler(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await safe_reply(update, "Доступ запрещен.")
        return
    records = await read_excel_data()
    if not records:
        await safe_reply(update, "История пуста.")
        return
    history_text = "📜 Последние 10 записей:\n\n" + "\n".join([
        f"Билет: {r[0]}, №: {r[1]}, Подр: {r[2]}, Дата: {r[3]}, Регион: {r[4]}, Оценка: {r[7]}"
        for r in records[-10:]
    ])
    await safe_reply(update, history_text)

async def download_month_handler(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await safe_reply(update, "Доступ запрещен.")
        return

    if not context.args:
        await safe_reply(update, "Использование: /download_month ММ.ГГГГ [Регион]")
        return

    month_text = context.args[0]
    bounds = get_month_bounds(month_text)
    if not bounds:
        await safe_reply(update, "Неверный формат. Используйте ММ.ГГГГ")
        return

    region = None
    if len(context.args) > 1:
        candidate = " ".join(context.args[1:])
        region = match_region_name(candidate)
        if not region:
            await safe_reply(update, "Неизвестный регион.")
            return

    start, end = bounds
    paths = await get_archive_paths(start, end, region)
    if not paths:
        await safe_reply(update, "Архивы не найдены.")
        return

    zip_path = await create_archive_zip(paths, f"archive_{month_text}")
    try:
        await send_document_from_path(context.bot, update.effective_chat.id, zip_path, caption=f"Архив {month_text}")
    finally:
        if zip_path.exists():
            zip_path.unlink()
