from aiogram import types
from misc import dp, bot, config
from keyboards.inline import submit_delete_account
from telegram_bot.utils.db import TelegramAccount, session
from ..start import start
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError


class TgAccountProxy(StatesGroup):
    ask_proxy = State()


# DELETE ACCOUNT
@dp.callback_query_handler(text_contains="list_account_functions:auto_answering:delete")
async def delete_account_question(callback: types.CallbackQuery):
    account_id = callback.data.split(':')[-1]
    await callback.message.edit_text("<i>Вы уверены, что хотите удалить аккаунт?</i>",
                                     reply_markup=submit_delete_account(account_id))


@dp.callback_query_handler(text_contains="list_account_functions:auto_posting:delete")
async def delete_account_question(callback: types.CallbackQuery):
    account_id = callback.data.split(':')[-1]
    await callback.message.edit_text("<i>Вы уверены, что хотите удалить аккаунт?</i>",
                                     reply_markup=submit_delete_account(account_id))


@dp.callback_query_handler(text_contains="delete_account:yes")
async def delete_account_submit(callback: types.CallbackQuery):
    account_id = callback.data.split(':')[-1]
    account = TelegramAccount.query.filter(TelegramAccount.id == account_id).first()

    try:
        session.delete(account)
        session.commit()
    except PendingRollbackError:
        session.rollback()

    await callback.answer("Аккаунт успешно удален!")
    await start(callback.message, is_editable_msg=True)


@dp.callback_query_handler(text_contains="delete_account:cancel")
async def delete_account_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await start(callback.message, is_editable_msg=True, state=state)


# CHANGE PROXY
@dp.callback_query_handler(text_contains="list_account_functions:auto_answering:change_proxy")
async def change_proxy_ask(callback: types.CallbackQuery, state: FSMContext):
    account_id = callback.data.split(':')[-1]

    await callback.message.delete_reply_markup()
    await callback.message.edit_text("Введите новый прокси для аккаунта в формате:\n"
                                     "<code>login:password@ip:port</code> (SOCKS)")
    await TgAccountProxy.ask_proxy.set()
    await state.update_data(account_id=account_id)


@dp.callback_query_handler(text_contains="list_account_functions:auto_posting:change_proxy")
async def change_proxy_ask(callback: types.CallbackQuery, state: FSMContext):
    account_id = callback.data.split(':')[-1]

    await callback.message.delete_reply_markup()
    await callback.message.edit_text("Введите новый прокси для аккаунта в формате:\n"
                                     "<code>login:password@ip:port</code> (SOCKS)")
    await TgAccountProxy.ask_proxy.set()
    await state.update_data(account_id=account_id)


@dp.message_handler(state=TgAccountProxy.ask_proxy)
async def change_proxy_set(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    account = TelegramAccount.query.filter(TelegramAccount.id == user_data.get('account_id')).first()

    if message.text.lower() == "отмена":
        await state.finish()
        await message.answer("Ввод отменен!")

    elif account and len(message.text.split("@")) == 2:
        account.proxy = message.text

        try:
            session.commit()
            await message.answer("Прокси для данного аккаунта обновлен!")
            await start(message, state=state)
        except PendingRollbackError:
            session.rollback()
            await message.answer("Произошла ошибка на стороне сервера!")
        await state.finish()

    else:
        await message.answer("Введите новый прокси для аккаунта в формате:\n"
                             "<code>login:password@ip:port</code> (SOCKS)\n\n"
                             "Либо введите <b>Отмена</b>")
        await TgAccountProxy.ask_proxy.set()
