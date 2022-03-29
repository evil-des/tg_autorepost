from aiogram import types
from misc import dp, bot, config
from telegram_bot.utils.variables import tg_accounts
from telegram_bot.utils.db import User, session, TelegramAccount
from keyboards.inline import add_proxy_menu, submit_account
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from telegram_bot.classes.TgAccount import TgAccount
from telethon.errors.rpcerrorlist import PhoneNumberInvalidError, SessionPasswordNeededError, PhoneCodeInvalidError, \
    PhoneCodeExpiredError
from telebot import TeleBot


class TelegramAccountData(StatesGroup):
    phone = State()
    proxy = State()
    validate = State()
    phone_code = State()
    password = State()


# HANDLERS
@dp.message_handler(state=TelegramAccountData.phone)
async def set_phone(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.finish()
        await message.answer("Ввод отменен!")

    elif message.text.strip("+").strip().isnumeric():
        await state.update_data(phone=int(message.text.strip("+").strip()))
        await message.answer("❕ <b>Введите прокси в формате: <code>login:password@ip:port (SOCKS)</code></b>",
                             reply_markup=add_proxy_menu())
        await TelegramAccountData.proxy.set()

    else:
        await message.answer("❕ Введите номер в верном формате, либо напишите <b>Отмена</b>")
        await TelegramAccountData.phone.set()


@dp.message_handler(state=TelegramAccountData.proxy)
async def set_proxy(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.finish()
        await message.answer("Ввод отменен!")

    elif len(message.text.split("@")) == 2:
        login_pass, ip_port = [x.split(":") for x in message.text.split("@")]  # парсим данные от прокси из строки
        login, password, ip, port = login_pass + ip_port

        await state.update_data(login=login, password=password, ip=ip, port=port)
        user_data = await state.get_data()

        await message.answer(f"📱 <b>Номер</b>: <code>{user_data.get('phone')}</code>\n"
                             f"📡 <b>Прокси</b>:\n"
                             f"|- <b>IP</b>: <code>{ip}</code>\n"
                             f"|- <b>LOGIN</b>: <code>{login}</code>\n"
                             f"|- <b>PASSWORD</b>: <code>{password}</code>\n"
                             f"|- <b>PORT</b>: <code>{port}</code>",
                             reply_markup=submit_account())
        await TelegramAccountData.validate.set()

    else:
        await message.answer("❕ Введите прокси в верном формате, либо напишите <b>Отмена</b>")
        await TelegramAccountData.proxy.set()


@dp.callback_query_handler(text="submit_account", state=TelegramAccountData.validate)
async def validate(callback: types.CallbackQuery, state: FSMContext):
    user = User.query.filter(User.chat_id == callback.message.chat.id).first()
    user_data = await state.get_data()

    account = TgAccount(phone=user_data.get('phone'))

    try:
        await state.update_data(account_id=account.id)
        await account.send_code_request()

        await callback.message.answer("💬 <b>Введите полученный код:</b>")
        await TelegramAccountData.phone_code.set()
    except PhoneNumberInvalidError:
        await callback.message.answer("Неверный номер телефона! Заполните все данные заново")
        await callback.message.answer("📱 <b>Введите номер от аккаунта Telegram (Без + и пробелов):</b>")

        await TelegramAccountData.phone.set()


@dp.message_handler(state=TelegramAccountData.validate)
async def validate_error(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление аккаунта отменено!")

    else:
        await message.answer("Нажмите на кнопку <b>Все верно</b>, если введеная вами информация корректна, "
                             "либо напишите <b>Отмена</b>")


@dp.message_handler(state=TelegramAccountData.phone_code)
async def set_phone_code(message: types.Message, state: FSMContext):
    user = User.query.filter(User.chat_id == message.chat.id).first()
    user_data = await state.get_data()
    account = tg_accounts.get(user_data.get('account_id'))

    if message.text.lower() == "отмена":
        await state.finish()
        await message.answer("Ввод отменен!")

    elif account and len(message.text) > 1 and message.text.isnumeric():
        await auth_account(user, account, message, state, user_data)

    else:
        await message.answer("💬 <b>Введите полученный код, либо напишите Отмена:</b>")
        await TelegramAccountData.phone_code.set()


@dp.message_handler(state=TelegramAccountData.password)
async def set_password(message: types.Message, state: FSMContext):
    user = User.query.filter(User.chat_id == message.chat.id).first()
    user_data = await state.get_data()
    account = tg_accounts.get(user_data.get('account_id'))

    if message.text.lower() == "отмена":
        await state.finish()
        await message.answer("Ввод отменен!")

    elif len(message.text) > 1:
        await auth_account(user, account, message, state, user_data, password=message.text.strip())
        await state.finish()


# util functions
async def auth_account(user, account, message, state, user_data, password=None):
    try:
        await account.auth(code=message.text, password=password)
        await add_account(account, user, message, user_data, state, password)

    except PhoneCodeInvalidError:
        await message.answer("Вы ввели неверный код! Отправьте новый, либо напишите <b>Отмена</b>:")
        await TelegramAccountData.phone_code.set()

    except PhoneCodeExpiredError:
        await message.answer("Код истек! Отправьте новый, либо напишите <b>Отмена</b>:")
        await TelegramAccountData.phone_code.set()

    except SessionPasswordNeededError:
        await message.answer("Введите пароль для двухфакторной аутентификации, либо введите <b>Отмена</b>:")
        await TelegramAccountData.password.set()


async def add_account(account, user, message, user_data, state, password=None):
    user_info = await account.get_user_info()
    proxy = f"{user_data.get('login')}:{user_data.get('password')}@{user_data.get('ip')}:{user_data.get('port')}"

    # создание объекта БД модели TelegramAccount
    account_ = TelegramAccount(user_id=user.id, chat_id=user_info.get('chat_id'),
                               phone=user_data.get('phone'), username=user_info.get('username'),
                               fullname=user_info.get('fullname'), password=password, proxy=proxy)

    try:
        # остановка сессии аккаунта и удаление его из общего пулла
        await account.stop()

        session.add(account_)
        session.commit()

        await message.answer("Аккаунт успешно добавлен! Вернитесь в основнога бота.")
        message_id, service = user_data.get('payload').split(':')

        # отправка сообщения в основного бота об успешном добавлении аккаунта
        bot_ = TeleBot(config['bot']['token'], parse_mode='html')
        # bot_.edit_message_reply_markup(user.chat_id, message_id,
        #                                reply_markup=list_tg_accounts(user.chat_id, service))
        bot_.send_message(user.chat_id, f"Аккаунт [<i>{user_data.get('phone')}</i>]  успешно добавлен!")
        await state.finish()

    except PendingRollbackError:
        session.rollback()
        await message.answer("Произошла ошибка на стороне бота. Повторите позже")
        await state.finish()
