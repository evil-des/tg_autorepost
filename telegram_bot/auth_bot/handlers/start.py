from aiogram import types
from aiogram.dispatcher import FSMContext
from telegram_bot.auth_bot.misc import dp, bot, config
from telegram_bot.utils.db import User, session
from aiogram.dispatcher import FSMContext
from .get_data import TelegramAccountData
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from aiogram.utils.deep_linking import decode_payload


@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    user = User.query.filter(User.chat_id == message.chat.id).first()
    args = message.get_args()
    payload = decode_payload(args)

    if user and payload:
        update_user(message)

        await message.answer("📱 <b>Введите номер от аккаунта Telegram (Без + и пробелов):</b>")

        await TelegramAccountData.phone.set()
        await state.update_data(payload=payload)
    else:
        await message.answer("Перейдите в основного бота и пропишите /start")


def update_user(message: types.Message):
    user = session.query(User).filter(User.chat_id == message.chat.id).first()
    if user:
        user.username = validate_username(message.chat.username)
        user.fullname = message.chat.full_name

        try:
            session.commit()
        except PendingRollbackError:
            session.rollback()

    return user


def validate_username(username):
    if username:
        return username.lower()
    return None

