from aiogram import types
from misc import dp, bot, config
from keyboards.inline import list_tg_accounts, list_account_functions
from telegram_bot.classes.TgAccount import TgAccount
from telegram_bot.utils.db import User, TelegramAccount, session
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from telegram_bot.main.handlers.start import start


class AddChat(StatesGroup):
    add_link = State()


@dp.callback_query_handler(text_contains="list_account_functions:auto_posting:add_chat")
async def add_chat_manually(callback: types.CallbackQuery, state: FSMContext):
    account_id = callback.data.split(':')[-1]
    account_ = TelegramAccount.query.filter(TelegramAccount.id == account_id).first()

    await state.update_data(account=account_)

    await callback.message.edit_text("Отправьте ссылку на новый чат, в формате - "
                                     "<code>https://t.me/[joinchat]/chat</code>:")
    await AddChat.add_link.set()


@dp.message_handler(state=AddChat.add_link)
async def add_link(message: types.Message, state: FSMContext):
    status, is_private = False, False

    if message.text.strip().lower() == "отмена":
        await start(message, state)
        return

    if message.text.startswith("https://t.me/"):
        link_parts = message.text[8:].split("/")

        data = await state.get_data()
        account_ = data.get("account")
        account = TgAccount(phone=account_.phone)
        await account.auth()

        entity = link_parts[-1]

        if len(link_parts) == 3 or \
                (len(link_parts) == 2 and "+" in entity):  # t.me/joinchat/<hash> -> 3 parts
            status, is_private = True, True

        elif len(link_parts) == 2:  # t.me/<chat> -> 2 parts
            status, is_private = True, False

        if status:
            try:
                await account.join_chat(entity.lstrip("+"), is_private=is_private)
                await message.answer("Чат успешно добавлен!")
                await start(message, state)
            except Exception as e:
                await message.answer("Произошла ошибка при обработке запроса. "
                                     "Отправьте новую ссылку, либо напишите Отмена:")
                await AddChat.add_link.set()
            return

    if not status:
        await message.answer("Ссылка имеет неверный формат! "
                             "Отправьте ссылку в формате – <code>https://t.me/[joinchat]/chat</code>, "
                             "либо напишите <b>Отмена</b>:")
        await AddChat.add_link.set()
