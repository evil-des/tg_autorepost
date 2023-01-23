from aiogram import types
from misc import dp, bot, config
from keyboards.inline import list_tg_accounts, list_account_functions
from telegram_bot.classes.TgAccount import TgAccount
from telegram_bot.utils.db import User, TelegramAccount, session
from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from aiogram.utils.exceptions import MessageNotModified
from telegram_bot.utils.variables import CHATS_LIMIT


@dp.callback_query_handler(text_contains="list_account_functions:auto_posting:download_chats")
async def show_account_settings_chats(callback: types.CallbackQuery, state: FSMContext):
    account_id = callback.data.split(':')[-1]
    account_ = TelegramAccount.query.filter(TelegramAccount.id == account_id).first()

    account = TgAccount(phone=account_.phone)
    await account.auth()
    chats = await account.get_chats()

    current_page = 0
    pages_num = len(chats) // CHATS_LIMIT
    await state.update_data(current_page=current_page,
                            pages_num=pages_num,
                            chats=chats,
                            account_id=account_id)

    page_info = {
        'current_page': current_page,
        'pages_num': pages_num
    }

    try:
        await callback.message.edit_reply_markup(
            reply_markup=list_account_functions(callback.data.split(":")[-1],
                                                service_name=callback.data.split(':')[1],
                                                chats=chats[
                                                      current_page:CHATS_LIMIT],
                                                page_info=page_info)
        )
    except MessageNotModified:
        if not chats:
            await callback.answer("⚠️ Диалоги не найдены!")
    except Exception as e:
        await callback.answer("Произошла непредвиденная ошибка!")


@dp.callback_query_handler(text_contains="list_account_functions:auto_posting:nav")
async def show_account_settings_chats_nav(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[-1]
    user_data = await state.get_data()
    current_page, chats = user_data.get('current_page'), user_data.get('chats')

    if action == "pages_num":
        await callback.answer("Используйте навигационные кнопки!")
        return
    elif action == "next":
        current_page += 1
    elif action == "back":
        current_page -= 1

    page_info = {
        'current_page': current_page,
        'pages_num': user_data.get('pages_num')
    }

    await state.update_data(current_page=current_page)
    if current_page <= user_data.get('pages_num'):
        try:
            await callback.message.edit_reply_markup(reply_markup=list_account_functions(user_data.get('account_id'),
                                                                                         service_name=
                                                                                         callback.data.split(':')[1],
                                                                                         chats=chats[
                                                                                               current_page * CHATS_LIMIT:CHATS_LIMIT],
                                                                                         page_info=page_info))
        except MessageNotModified:
            if not chats:
                await callback.answer("⚠️ Диалоги не найдены!")
