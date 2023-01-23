from aiogram import types
from misc import dp, bot, config
from telegram_bot.utils.db import User, session
from keyboards.inline import choose_service_kb
from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError


@dp.message_handler(state="*", commands=['start'])
async def start(message: types.Message, state: FSMContext, is_editable_msg=False):
    await state.finish()
    await state.reset_data()
    try:
        register_user(message)
    except IntegrityError:
        session.rollback()
        update_user(message)

    if not is_editable_msg:
        await message.answer("Выберите нужный пункт меню:", reply_markup=choose_service_kb())
    else:
        await message.edit_text("Выберите нужный пункт меню:", reply_markup=choose_service_kb())


def register_user(message: types.Message):
    username = validate_username(message.chat.username)

    user = User(chat_id=message.chat.id, username=username, fullname=message.chat.full_name)
    session.add(user)

    try:
        session.commit()
    except PendingRollbackError:
        session.rollback()

    return user


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

