
from aiogram import types


def start_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('')
    
    return keyboard
