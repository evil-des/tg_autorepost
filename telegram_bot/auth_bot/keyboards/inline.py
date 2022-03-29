from aiogram import types
from misc import config


def add_proxy_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        types.InlineKeyboardButton('📜 Инструкция', url=config['auth_bot']['proxy_guide_link']),
        types.InlineKeyboardButton('➕ Купить прокси', url=config['auth_bot']['buy_proxy_link'])
    )

    return keyboard


def submit_account():
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        types.InlineKeyboardButton('Все верно', callback_data="submit_account")
    )

    return keyboard