import logging
import os
import sys

from dotenv import load_dotenv
from telegram import (Bot, KeyboardButton, ReplyKeyboardMarkup,
                      ReplyKeyboardRemove, TelegramError)
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from typograf import Typograf, TypografEntityType

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_PORT = int(os.environ.get('TELEGRAM_PORT', '8443'))
HEROKU_URL = os.getenv('HEROKU_URL')

WELCOME_TEXT = (
    'Типограф — это инструмент, который приводит текст в соответствие '
    'с правилами экранной типографики:\n'
    '  — меняет неправильные кавычки на «елочки» и «лапки»;\n'
    '  — проставляет неразрывные пробелы;\n'
    '  — ставит тире вместо дефиса;\n'
    '  — убирает лишние пробелы;\n'
    '  — меняет (с) на © и т.д.\n\n'
    'Отправь мне сообщение с каким-нибудь текстом и увидишь, '
    'что получится.\n\n'
    'Меня можно немного настроить, используй команду /set_type'
)
EXCEPTION_MESSAGE = ('Что-то пошло не так, мы обязательно разберёмся c этим. '
                     'Приносим извинения за неудобства.')
UNKNOWN_MESSAGE = 'Я не умею с этим работать :('
SET_TYPE_MESSAGE = (
    'Выбери один из варинатов:\n'
    '  — LETTER - верну заменяемые символы буквенным кодом;\n'
    '  — NUMBER - верну заменяемые символы числовым кодом;\n'
    '  — SYMBOL - верну готовый текст;\n'
)


def send_message(bot: Bot, chat_id: int, text: str, reply_markup=None) -> None:
    try:
        bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except TelegramError as error:
        logger.exception(error)


def unknown(update, context) -> None:
    send_message(
        context.bot,
        update.effective_chat.id,
        UNKNOWN_MESSAGE
    )


def start(update, context) -> None:
    send_message(context.bot, update.effective_chat.id, WELCOME_TEXT)


def get_keyboard_markup(remove: bool = False):
    if not remove:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(f'/set_type {item.name}') for item in TypografEntityType]
            ],
            resize_keyboard=True
        )
    return ReplyKeyboardRemove()


def set_type(update, context) -> None:
    markup = get_keyboard_markup()
    text = SET_TYPE_MESSAGE

    if context.args:
        try:
            context.chat_data['typograf'] = Typograf(
                entity_type=TypografEntityType[context.args[0]]
            )
            markup = get_keyboard_markup(True)
            text = 'Отлично, давай проверим как это работает?'
        except KeyError:
            text = 'Выбрано недопустимое значение, давай попробуем еще раз.'
            markup = get_keyboard_markup()

    send_message(
        context.bot, update.effective_chat.id, text, reply_markup=markup
    )


def message(update, context) -> None:
    typograf = context.chat_data.get('typograf', Typograf())
    try:
        text = typograf.process_text(update.message.text)
    except Exception as error:
        logger.exception(error)
        text = EXCEPTION_MESSAGE
    finally:
        send_message(context.bot, update.effective_chat.id, text)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s [%(levelname)s] - '
            '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
        ),
        handlers=[
            logging.FileHandler(f'{BASE_DIR}/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    updater = Updater(token=TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    set_type_handler = CommandHandler('set_type', set_type)
    dispatcher.add_handler(set_type_handler)

    message_handler = MessageHandler(Filters.text & (~Filters.command), message)
    dispatcher.add_handler(message_handler)

    unknown_handler = MessageHandler(Filters.all & (~Filters.command) & (~Filters.text), unknown)
    dispatcher.add_handler(unknown_handler)

    updater.start_webhook(
        listen="0.0.0.0",
        port=TELEGRAM_PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=HEROKU_URL + TELEGRAM_TOKEN
    )
    updater.idle()
