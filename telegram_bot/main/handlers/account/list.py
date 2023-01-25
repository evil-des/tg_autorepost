from aiogram import types
from aiogram.dispatcher import FSMContext
from misc import dp, bot, config
from keyboards.inline import list_tg_accounts, list_account_functions
from ..start import start
from telegram_bot.utils.db import TelegramAccount
# from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters.state import State, StatesGroup
from telegram_bot.utils.variables import CHATS_LIMIT


@dp.callback_query_handler(text_contains="choose_service")
async def show_accounts(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await state.reset_data()

    await callback.message.edit_text("💡 <i>Выберите нужный аккаунт или добавьте новый:</i>",
                                     reply_markup=list_tg_accounts(callback.message.chat.id,
                                                                   service_name=callback.data.split(':')[1]))


@dp.callback_query_handler(state="*", text_contains="list_tg_accounts:account")
async def show_account_settings(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await state.reset_data()
    account_id, service = callback.data.split(':')[-1], callback.data.split(':')[-2]

    if "auto_answering:switch" in callback.data:
        account_id, service = callback.data.split(':')[-1], callback.data.split(':')[1]

    account = TelegramAccount.query.filter(TelegramAccount.id == account_id).first()

    msg_text = f"📱 <b>Номер:</b> <code>{account.phone}</code>\n" \
               f"📡 <b>Прокси:</b> <code>{account.proxy}</code>"

    if service == 'auto_answering':
        # доп. данные об аккаунте для сервиса автоответчика
        text = "Не установлен" if not account.answering_text else account.answering_text
        msg_text += f"\n📄 <b>Текст автоответчика:</b> <code>{text}</code>"

        status = "Работает" if account.answering_status else "Не работает"
        msg_text += f"\n⚖️ <b>Статус:</b> <code>{status}</code>"

    # if not user_data.get('chats'):
    #     await callback.message.edit_text(msg_text, reply_markup=list_account_functions(account_id, service_name=service))
    # else:
    #     chats = user_data.get('chats')
    #     current_page = user_data.get('current_page')
    #     page_info = {
    #         'current_page': current_page,
    #         'pages_num': user_data.get('pages_num')
    #     }
    #     await callback.message.edit_text(msg_text,
    #                                      reply_markup=list_account_functions(account_id, service_name=service,
    #                                                                          chats=chats[
    #                                                                                current_page * CHATS_LIMIT:CHATS_LIMIT],
    #                                                                          page_info=page_info
    #                                                                          ))
    await callback.message.edit_text(msg_text,
                                     reply_markup=list_account_functions(account_id,
                                                                         service_name=service)
                                     )


@dp.callback_query_handler(text_contains="list_tg_accounts:back")
async def back(callback: types.CallbackQuery, state: FSMContext):
    await start(callback.message, state=state, is_editable_msg=True)


@dp.callback_query_handler(text=["list_account_functions:auto_posting:back",
                                 "list_account_functions:auto_answering:back"])
async def back(callback: types.CallbackQuery, state: FSMContext):
    await show_accounts(callback, state)
