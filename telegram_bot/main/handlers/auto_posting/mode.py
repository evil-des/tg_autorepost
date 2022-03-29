from aiogram import types
from misc import dp, bot, config
from keyboards.inline import choose_posting_mode_kb, list_account_functions, submit_post_kb, posting_settings_kb
from telegram_bot.classes.TgAccount import TgAccount
from telegram_bot.utils.db import User, TelegramAccount, session, PostingConfig
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


@dp.callback_query_handler(state='*', text_contains="list_account_functions:multi_settings")
async def multi_settings(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Не до конца реализовано")
    await PostingMode.choose_mode.set()


@dp.callback_query_handler(state='*', text_contains="list_account_functions:auto_posting:chat")
async def choose_posting_mode(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Выберите режим работы:',
                                     reply_markup=choose_posting_mode_kb("auto_posting", callback.data.split(':')[-1],
                                                                         callback.data.split(':')[-2]))
    await PostingMode.choose_mode.set()


@dp.callback_query_handler(state=PostingMode.choose_mode, text_contains="choose_posting_mode:favorite")
async def posting_mode_fav(callback: types.CallbackQuery, state: FSMContext):
    chat_id, account_id = callback.data.split(':')[2:]
    await state.reset_data()
    await state.update_data(chat_id=chat_id, account_id=account_id, mode="favorite")

    await posting_settings(callback.message, state)
    await PostingMode.posting_settings.set()


@dp.callback_query_handler(state=PostingMode.choose_mode, text_contains="choose_posting_mode:manual")
async def posting_mode_manual(callback: types.CallbackQuery, state: FSMContext):
    chat_id, account_id = callback.data.split(':')[2:]
    await state.reset_data()
    await state.update_data(chat_id=chat_id, account_id=account_id, mode="manual")

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
        account = TelegramAccount.query.filter(TelegramAccount.id == user_data.get('account_id')).first()

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
    account = TelegramAccount.query.filter(TelegramAccount.id == user_data['account_id']).first()
    config_ = PostingConfig.query.filter(PostingConfig.account_id == account.id and
                                         PostingConfig.channel_id == user_data.get('channel_id')).first()
    if not config_:
        config_ = PostingConfig(account_id=account.id, mode=user_data['mode'], chat_id=user_data['chat_id'])

    if user_data['mode'] == 'manual':
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

    session.add(config_)
    session.commit()

    await state.update_data(config_id=config_.id)
    schedule_text = f'{"каждые " + config_.schedule + " мин." if config_.schedule.isnumeric() else config_.schedule}'
    msg_text = f'Параметры автопостинга:\n\n'\
               f'ID чата/канала сообщ.: <code>{config_.channel_id}</code>\n'\
               f'ID сообщения: <code>{config_.message_id}</code>\n'\
               f'Источник сообщ.: <code>{"канал/чат" if config_.mode == "manual" else "Избранное"}</code>'\
               f'\n\nС закреплением: <code>{"да" if config_.pin else "нет"}</code>\n'\
               f'С уведомлением: <code>{"да" if config_.notification else "нет"}</code>\n'\
               f'Расписание постов: <code>{schedule_text}</code>'
    reply_markup = posting_settings_kb(user_data['account_id'], config_)

    try:
        await message.edit_text(msg_text, reply_markup=reply_markup)
    except MessageCantBeEdited:
        await message.answer(msg_text, reply_markup=reply_markup)

