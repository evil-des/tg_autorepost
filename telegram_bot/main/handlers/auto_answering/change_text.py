from aiogram import types
from misc import dp, bot, config
from keyboards.inline import submit_delete_account
from telegram_bot.utils.db import TelegramAccount, session
from ..start import start
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError


class AnsweringText(StatesGroup):
    ask_new_text = State()


@dp.callback_query_handler(text_contains="list_account_functions:auto_answering:change_text")
async def change_text_ask(callback: types.CallbackQuery, state: FSMContext):
    account_id = callback.data.split(':')[-1]

    await callback.message.delete_reply_markup()
    await callback.message.edit_text("Введите новый текст для автоответчика:")
    await AnsweringText.ask_new_text.set()
    await state.update_data(account_id=account_id)


@dp.message_handler(state=AnsweringText.ask_new_text)
async def change_text_set(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    account = TelegramAccount.query.filter(TelegramAccount.id == user_data.get('account_id')).first()

    if message.text.lower() == "отмена":
        await state.finish()
        await message.answer("Ввод отменен!")

    elif account and len(message.text) > 1:
        account.answering_text = message.text.strip()

        try:
            session.commit()
            await message.answer("Текс для автоответчика обновлен!")
            await start(message, state=state)
        except PendingRollbackError:
            session.rollback()
            await message.answer("Произошла ошибка на стороне сервера!")
        await state.finish()

    else:
        await message.answer("Введите новый текст для автоответчика, либо введите <b>Отмена</b>:")
        await AnsweringText.ask_new_text.set()
