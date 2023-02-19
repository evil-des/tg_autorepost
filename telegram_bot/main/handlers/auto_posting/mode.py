import sqlalchemy.exc
from aiogram import types
from misc import dp, bot, config
from keyboards.inline import choose_posting_mode_kb, list_account_functions, submit_post_kb, posting_settings_kb
from telegram_bot.classes.TgAccount import TgAccount
from telegram_bot.utils.db import User, TelegramAccount, session, PostingConfig, MultiSettings
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from aiogram.utils.exceptions import MessageCantBeEdited


class PostingMode(StatesGroup):
    choose_mode = State()
    ask_post_link = State()
    validate_post = State()
    submit_post = State()
    posting_settings = State()
    settings_ask_time = State()


@dp.callback_query_handler(state='*', text_contains="list_account_functions:auto_posting:multi_settings")
async def multi_settings(callback: types.CallbackQuery, state: FSMContext):
    # await state.reset_data()
    account_id = callback.data.split(":")[-1]
    await callback.message.edit_text('Выберите режим работы:',
                                     reply_markup=choose_posting_mode_kb("auto_posting", account_id,
                                                                         is_multi_settings=True))
    await PostingMode.choose_mode.set()


@dp.callback_query_handler(state='*', text_contains="list_account_functions:auto_posting:chat")
async def choose_posting_mode(callback: types.CallbackQuery, state: FSMContext, is_change_source=False):
    account_id, chat_id = callback.data.split(':')[-1], callback.data.split(':')[-2]

    if not is_change_source:
        config_ = PostingConfig.query.filter(PostingConfig.account_id == account_id).first()

        if config_:
            await state.reset_data()
            await state.update_data(config=config_)

            await posting_settings(callback.message, state)
            await PostingMode.posting_settings.set()
            return

    await callback.message.edit_text('Выберите режим работы:',
                                     reply_markup=choose_posting_mode_kb("auto_posting",
                                                                         account_id, chat_id))
    await PostingMode.choose_mode.set()


@dp.callback_query_handler(state=PostingMode.choose_mode, text_contains="choose_posting_mode")
async def set_posting_mode(callback: types.CallbackQuery, state: FSMContext):
    chat_id, account_id, is_multi_settings = callback.data.split(':')[2:]
    mode = callback.data.split(":")[1]

    await state.update_data(chat_id=int(chat_id), account_id=int(account_id), mode=mode,
                            is_multi_settings=bool(int(is_multi_settings)))

    if mode == "favorite":
        await posting_settings(callback.message, state)
        await PostingMode.posting_settings.set()
    else:
        await callback.message.edit_text('Введите ссылку на пост:')
        await PostingMode.ask_post_link.set()


@dp.message_handler(state=PostingMode.ask_post_link)
async def set_post_link(message: types.Message, state: FSMContext):
    if message.text.lower() == 'отмена':
        await state.finish()
        await message.answer("Ввод отменен!")

    elif "https://" in message.text:
        await state.update_data(post=message.text.strip())
        user_data = await state.get_data()
        print(user_data)
        if user_data.get("account"):
            account = user_data.get("account")
        else:
            account = TelegramAccount.query.filter(TelegramAccount.id == user_data.get('account_id')).first()
        print(account)

        tg_account = TgAccount(phone=account.phone)
        await tg_account.auth()

        message_ = await tg_account.get_message_by_link(link=message.text.strip())
        await tg_account.forward_message(entity=message.chat.id, from_peer=message_.chat.id, message_id=message_.id)
        await message.answer(f"Аккаунт [{account.phone}] переслал вам сообщение. Оно верное?",
                             reply_markup=submit_post_kb(message_.chat.id, message_.id, account.id))
        await PostingMode.submit_post.set()

    else:
        await message.answer('Введите ссылку на пост, либо введите <b>Отмена</b>:')
        await PostingMode.ask_post_link.set()


@dp.callback_query_handler(state=PostingMode.submit_post, text_contains="submit_post:yes")
async def submit_post_yes(callback: types.CallbackQuery, state: FSMContext):
    channel_id, post_id, account_id = callback.data.split(':')[2:]
    await state.update_data(channel_id=channel_id, post_id=post_id, account_id=account_id)
    await posting_settings(callback.message, state)
    await PostingMode.posting_settings.set()


@dp.callback_query_handler(state=PostingMode.submit_post, text_contains="submit_post:cancel")
async def submit_post_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Введите ссылку на пост:')
    await PostingMode.ask_post_link.set()


@dp.message_handler(state=PostingMode.submit_post)
async def submit_post_msg(message: types.Message, state: FSMContext):
    await message.answer("Подтвердите действие сверху 👆")


@dp.message_handler(state=PostingMode.posting_settings)
async def posting_settings(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    config_, account = await get_config_and_account(user_data)
    await add_message_source(user_data, config_, account, message)
    await state.update_data(config_id=config_.id)

    msg_text = await get_formatted_message(config_)
    keyboard = posting_settings_kb(account.id, config_,
                                   is_another_back_btn=bool(user_data.get("config")))
    try:
        await message.edit_text(msg_text, reply_markup=keyboard)
    except MessageCantBeEdited:
        await message.answer(msg_text, reply_markup=keyboard)


async def add_message_source(user_data, config_, account, message: types.Message):
    if user_data.get("mode") == 'manual':
        config_.channel_id = user_data['channel_id']
        config_.message_id = user_data['post_id']
    else:
        tg_account = TgAccount(phone=account.phone)
        await tg_account.auth()
        message_ = await tg_account.get_fav_message(account.chat_id)
        if message:
            config_.channel_id = message_.chat.id
            config_.message_id = message_.id
        else:
            await message.answer("Ошибка. Отсутствуют избранные сообщения! (учит. только последнее)")

    config_.mode = user_data.get("mode")

    try:
        session.add(config_)
        session.commit()
    except sqlalchemy.exc.InvalidRequestError:
        return


async def get_config_and_account(user_data):
    if not user_data.get("config"):
        account = TelegramAccount.query.filter(TelegramAccount.id == user_data['account_id']).first()
        config_ = PostingConfig.query.filter(PostingConfig.account_id == account.id and
                                             PostingConfig.channel_id == user_data.get('channel_id')).first()
    else:
        config_ = user_data["config"]
        account = TelegramAccount.query.filter(TelegramAccount.id == config_.account_id).first()

    # TODO add config as Multi Settings
    if user_data.get("is_multi_settings"):
        config_ = MultiSettings.query.filter(MultiSettings.account_id == account.id).first()

    if not config_:
        config_ = PostingConfig(account_id=account.id, mode=user_data['mode'],
                                chat_id=user_data['chat_id'])
    elif not config_ and user_data.get("is_multi_settings"):
        config_ = MultiSettings(account_id=account.id, mode=user_data['mode'],
                                chat_id=user_data['chat_id'])
    return config_, account


async def get_formatted_message(config_):
    schedule_text = f'{"каждые " + config_.schedule + " мин." if config_.schedule.isnumeric() else config_.schedule}'
    msg_text = f'Параметры автопостинга:\n\n' \
               f'ID чата/канала сообщ.: <code>{config_.channel_id}</code>\n' \
               f'ID сообщения: <code>{config_.message_id}</code>\n' \
               f'Источник сообщ.: <code>{"канал/чат" if config_.mode == "manual" else "Избранное"}</code>' \
               f'\n\nС закреплением: <code>{"да" if config_.pin else "нет"}</code>\n' \
               f'С уведомлением: <code>{"да" if config_.notification else "нет"}</code>\n' \
               f'Расписание постов: <code>{schedule_text}</code>'
    return msg_text
