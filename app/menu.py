import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Функции для создания клавиатур ---
def build_menu(buttons, n_cols=1):
    return [buttons[i: i + n_cols] for i in range(0, len(buttons), n_cols)]


def get_keyboard(options, callback_prefix):
    keyboard = []
    for opt in options:
        # Для колбэка используем префикс + индекс опции, чтобы потом легко распарсить
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"{callback_prefix}_{options.index(opt)}")])
    return InlineKeyboardMarkup(keyboard)


def get_simple_keyboard(buttons_dict):
    """Создает клавиатуру из словаря {текст: callback_data}"""
    keyboard = []
    for text, callback in buttons_dict.items():
        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(keyboard)
