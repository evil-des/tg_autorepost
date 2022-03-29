from aiogram import types
from misc import dp, bot, config
from keyboards.inline import list_tg_accounts, list_account_functions
from telegram_bot.utils.db import TelegramAccount, session
from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters.state import State, StatesGroup
import logging
from ..account.list import show_account_settings
from telegram_bot.classes.TgAccount import TgAccount


@dp.callback_query_handler(text_contains="list_account_functions:auto_answering:switch")
async def show_accounts(callback: types.CallbackQuery, state: FSMContext):
    account_id = callback.data.split(':')[-1]
    account = TelegramAccount.query.filter(TelegramAccount.id == account_id).first()
    account.answering_status = True if not account.answering_status else False

    try:
        if not account.answering_text:
            await callback.answer("⚠️ Текст для автоответчика не установлен!")
            session.rollback()
            return

        tg_account = TgAccount(phone=account.phone)
        await tg_account.auth()

        if account.answering_status:
            await tg_account.start_auto_answering()
        else:
            await tg_account.stop_auto_answering()

        session.commit()
        await callback.answer("Статус работы автоответчика изменен!")
        await show_account_settings(callback, state=state)

    except Exception as e:
        logging.error(e)
        session.rollback()
        session.commit()
        await callback.answer("Произошла ошибка в запуске автоответчика!")
