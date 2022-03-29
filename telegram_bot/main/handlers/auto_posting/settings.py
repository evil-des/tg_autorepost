from aiogram import types
from misc import dp, bot, config
from keyboards.inline import choose_posting_mode_kb, list_account_functions, posting_settings_kb
from telegram_bot.classes.TgAccount import TgAccount
from telegram_bot.utils.db import User, TelegramAccount, session, PostingConfig
from ..start import start
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from .mode import posting_settings, PostingMode
import datetime


@dp.callback_query_handler(state=PostingMode.posting_settings, text_contains="posting_settings:pin")
async def setting_pin(callback: types.CallbackQuery, state: FSMContext):
    account_id, config_id = callback.data.split(':')[2:]
    config_ = PostingConfig.query.filter(PostingConfig.id == config_id).first()

    config_.pin = True if not config_.pin else False
    session.commit()

    await posting_settings(callback.message, state)
    await callback.answer("Статус закрепления сообщения изменен!")


@dp.callback_query_handler(state=PostingMode.posting_settings, text_contains="posting_settings:notification")
async def settings_notification(callback: types.CallbackQuery, state: FSMContext):
    account_id, config_id = callback.data.split(':')[2:]
    config_ = PostingConfig.query.filter(PostingConfig.id == config_id).first()

    config_.notification = True if not config_.notification else False
    session.commit()

    await posting_settings(callback.message, state)
    await callback.answer("Статус уведомлений при отправке сообщения изменен!")


@dp.callback_query_handler(state=PostingMode.posting_settings, text_contains="posting_settings:delete")
async def settings_delete(callback: types.CallbackQuery, state: FSMContext):
    account_id, config_id = callback.data.split(':')[2:]
    config_ = PostingConfig.query.filter(PostingConfig.id == config_id).first()
    await state.update_data(account_id=account_id, config_id=config_id)

    session.delete(config_)
    session.commit()

    await callback.answer("Конфиг успешно удален!")
    await start(callback.message, state, is_editable_msg=True)
    await state.finish()


@dp.callback_query_handler(state=PostingMode.posting_settings, text_contains="posting_settings:back")
async def settings_back(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    await callback.message.edit_text('Выберите режим работы:',
                                     reply_markup=choose_posting_mode_kb("auto_posting", user_data['account_id'],
                                                                         user_data['chat_id']))
    await PostingMode.choose_mode.set()


# SCHEDULING
@dp.callback_query_handler(state=PostingMode.posting_settings, text_contains="posting_settings:schedule")
async def settings_schedule(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split(':')[2]
    await state.update_data(schedule_mode=mode)
    if mode == 'minutes':
        text = "Введите задержку между постами в минутах:"
    else:
        text = "Введите расписание для постов в формате <code>12:00</code>:"

    await callback.message.edit_text(text)
    await PostingMode.settings_ask_time.set()


@dp.message_handler(state=PostingMode.settings_ask_time)
async def settings_set_time(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    config_ = PostingConfig.query.filter(PostingConfig.id == user_data['config_id']).first()
    status = False

    if message.text.lower().strip() == "отмена":
        await PostingMode.posting_settings.set()
        await posting_settings(message, state)

    elif len(message.text.strip().split()) == 1 and message.text.strip().isnumeric():
        status = True

    elif len(message.text.strip().split()) == 1 and is_valid_date(message.text.strip()):
        status = True

    elif len(message.text.strip().split()) > 1:
        status = True

    else:
        await message.answer("Неверный формат ввода, попробуйте еще раз, либо напишите <b>Отмена</b>:")
        await PostingMode.settings_ask_time.set()

    if status:
        config_.schedule = message.text.strip()
        if message.text.strip().isnumeric() and int(message.text) == 0:
            config_.schedule = "Не установлено"

        session.commit()
        await PostingMode.posting_settings.set()
        await posting_settings(message, state)


def is_valid_date(date: str):
    try:
        datetime.datetime.strptime(date, '%H:%M')
        return True
    except ValueError:
        return False
