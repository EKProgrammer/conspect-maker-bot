import logging

from telegram import Update, BotCommand, constants
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters)

from request_handling import beginning_of_request, detection_file, set_output_format

from config import TELEGRAM_BOT_TOKEN

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка сообщения при выполнении команды /start."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Здравствуйте, {user.mention_html()}! Это бот, который умеет конспектировать лекции. В меню указаны доступные команды."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка сообщения при выполнении команды /help."""
    await update.message.reply_text("""<u><b>Справка команд</b></u>:
/start - перезапуск бота;
/help - справка;
/request - сделать запрос.
В остальных случаях ожидается ссылка на аудио или видео.
=======================================================
<u><b>Формат ссылок</b></u>:
- <u><i>Youtube</i></u>: https://www.youtube.com/watch?v=идентификатор_видео
Замечание: у видео не должен быть установлен ограниченный доступ.
- <u><i>Google.Drive</i></u>: https://drive.google.com/file/d/идентификатор_файла/view?usp=sharing
Предварительно поставьте уровень доступа к файлу: "Все, у кого есть ссылка".
- <u><i>Yandex.Disk</i></u>: https://disk.yandex.ru/тип_файла/идентификатор_файла
Предварительно необходимо изменить уровень доступа файла по ссылке.
- <u><i>Telegram</i></u>: просто пришлите файл в этот чат
Разрешённые форматы для аудио: mp3, LPCM, OggOpus.
<u><i>Важно</i></u>: у видео будет взят во внимание только аудиопоток.
У файлов с дисков установлено ограничение на размер в 5 Гбайт.
Также видео или аудио должно иметь длительность не более 2 часов.""",
                                    disable_web_page_preview=True,
                                    parse_mode=constants.ParseMode.HTML)


async def make_menu(application: Application) -> None:
    """Создание меню"""
    command_info = [
        BotCommand("start", "Перезапуск бота"),
        BotCommand("help", "Cправка"),
        BotCommand("request", "Cделать запрос"),
    ]
    bot = application.bot
    await bot.set_my_commands(commands=command_info)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Остановка попытки запроса"""
    pass


def main() -> None:
    """Запуск бота"""
    # Создать приложение, ввести токен, сделать меню.
    application = (Application.builder()
                   .token(TELEGRAM_BOT_TOKEN)
                   .post_init(make_menu)
                   .build())

    # Команды
    command_handlers = [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
    ]
    application.add_handlers(command_handlers)

    # Cценарий для запроса для обработки
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("request", beginning_of_request)],
        states={
            1: [MessageHandler(filters.ALL & ~filters.COMMAND, detection_file)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_output_format)]
        },
        fallbacks=[CommandHandler("stop", stop)]
    ))

    # Бот работает до тех пор, пока пользователь не нажмет Ctrl-Cfilters.TEXT
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
