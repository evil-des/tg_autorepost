from aiogram import types
from misc import dp, bot, config
from keyboards.inline import add_account_menu
# from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from aiogram.utils.deep_linking import encode_payload


@dp.callback_query_handler(text_contains="list_tg_accounts:add")
async def add_account(callback: types.CallbackQuery):
    service_name = callback.data.split(':')[-1]
    link = f"https://t.me/{config['auth_bot']['username']}?start={encode_payload(callback.id + ':' + service_name)}"

    await callback.message.edit_text(f"⚡ <i>Перейдите в бота по "
                                     f"<a href=\"{link}\">ссылке</a> "
                                     f"и пройдите авторизацию, следуя дальнейшим инструкциям.</i>",
                                     reply_markup=add_account_menu(link))
