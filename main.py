import os
import logging
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Читаем токен из переменной окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Дата события (например, 31 декабря 2023 года)
EVENT_DATE = datetime(2027, 3, 28)

# Функция для отправки сообщения
async def send_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.data['chat_id']
    current_date = datetime.now()
    days_left = (EVENT_DATE - current_date).days

    if days_left > 0:
        message = f"До события осталось {days_left} дней!"
    elif days_left == 0:
        message = "Сегодня событие!"
    else:
        message = "Событие уже прошло!"

    logger.info(f"Отправка сообщения пользователю {chat_id}: {message}")
    try:
        await context.bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Сообщение успешно отправлено пользователю {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

# Команда /start для запуска рассылки
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    job_removed = remove_job_if_exists(str(chat_id), context)

    # Запуск задачи каждый день в 20:04:40
    target_time = time(hour=20, minute=4, second=40)
    now = datetime.now()
    today_target_time = datetime.combine(now.date(), target_time)

    if now >= today_target_time:
        # Если текущее время уже прошло 20:04:40, планируем задачу на следующий день
        next_day_target_time = today_target_time + timedelta(days=1)
        context.job_queue.run_once(send_message, next_day_target_time - now, data={'chat_id': chat_id}, name=str(chat_id))
        logger.info(f"Задача запланирована на {next_day_target_time} для пользователя {chat_id}")
    else:
        # Если текущее время еще до 20:04:40, планируем задачу на сегодня
        context.job_queue.run_daily(send_message, time=target_time, data={'chat_id': chat_id}, name=str(chat_id))
        logger.info(f"Задача запланирована на каждый день в 20:04:40 для пользователя {chat_id}")

    text = "Рассылка запущена! Каждый день в 20:04:40 я буду сообщать о количестве дней до события."
    if job_removed:
        text += " Старая задача была удалена."

    # Создаем кнопки
    keyboard = [
        [InlineKeyboardButton("Старт", callback_data='start')],
        [InlineKeyboardButton("Стоп", callback_data='stop')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)

# Команда /stop для остановки рассылки
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Рассылка остановлена." if job_removed else "Рассылка не запущена."

    # Создаем кнопки
    keyboard = [
        [InlineKeyboardButton("Старт", callback_data='start')],
        [InlineKeyboardButton("Стоп", callback_data='stop')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)

# Обработчик нажатий на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'start':
        await start(update, context)
    elif query.data == 'stop':
        await stop(update, context)

# Удаление существующей задачи
def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
        logger.info(f"Задача {job.name} удалена")
    return True

def main() -> None:
    # Создаем Application и передаем ему токен вашего бота
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    # Регистрируем обработчик нажатий на кнопки
    application.add_handler(CallbackQueryHandler(button))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
