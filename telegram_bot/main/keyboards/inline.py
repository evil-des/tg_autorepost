from aiogram import types
from telegram_bot.utils.db import User, TelegramAccount


def choose_service_kb():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        {'title': '⌛ Автопостинг', 'c_back': "auto_posting"},
        {'title': '💬 Автоответчик', 'c_back': "auto_answering"}
    ]

    keyboard.row(
        *[types.InlineKeyboardButton(button['title'], callback_data=f"choose_service:{button['c_back']}")
          for button in buttons]
    )

    return keyboard


# handlers -> account
def list_tg_accounts(chat_id, service_name):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        {'title': '➕ Добавить аккаунт', 'c_back': "add"},
        {'title': '🔙 Назад', 'c_back': "back"}
    ]

    # show list of added accounts
    user = User.query.filter(User.chat_id == chat_id).first()
    accounts = TelegramAccount.query.filter(TelegramAccount.user_id == user.id).all()

    keyboard.add(
        *[types.InlineKeyboardButton(account.phone,
                                     callback_data=f"list_tg_accounts:account:{service_name}:{account.id}")
          for account in accounts]
    )

    keyboard.add(
        *[types.InlineKeyboardButton(button['title'],
                                     callback_data=f"list_tg_accounts:{button['c_back']}:{service_name}")
          for button in buttons]
    )

    return keyboard


def add_account_menu(link):
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        types.InlineKeyboardButton('📡 Перейти', url=link),
        types.InlineKeyboardButton('🔙 Назад', callback_data=f"choose_service:back")
    )

    return keyboard


def list_account_functions(account_id, service_name, chats=None, page_info=None):
    account = TelegramAccount.query.filter(TelegramAccount.id == account_id).first()
    buttons = [
        # auto_posting
        {'title': '🔄 Загрузить чаты с аккаунта', 'c_back': f"download_chats:{account.id}", "order": "row",
         "service": "auto_posting"},
        {'title': '⬇️ Добавить чат вручную', 'c_back': f"add_chat:{account.id}", "order": "row",
         "service": "auto_posting"},

        # auto_answering
        {'title': '💬 Смена текста', 'c_back': f"change_text:{account.id}", "order": "cell",
         "service": "auto_answering"},
        {'title': '💡 Вкл/Выкл автоответчик', 'c_back': f"switch:{account.id}", "order": "cell",
         "service": "auto_answering"},

        # in both menus
        {'title': '🌏 Смена прокси', 'c_back': f"change_proxy:{account.id}", "order": "cell"},
        {'title': '🗑️ Удалить аккаунт', 'c_back': f"delete:{account.id}", "order": "cell"},
        {'title': '🔙 Назад', 'c_back': f"back", "order": "cell"},

        # auto_posting
        {'title': '📚 Multi settings', 'c_back': f"multi_settings:{account.id}", "order": "cell", "service": "auto_posting"}
    ]

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    if chats:
        nav_buttons = [
            {'title': f'{page_info["current_page"] + 1} / {page_info["pages_num"] + 1}', 'c_back': f"nav:pages_num"},
            {'title': '⬅️ Назад', 'c_back': f"nav:back"},
            {'title': 'Вперед ➡️', 'c_back': f"nav:next"},
        ]

        keyboard.add(
            *[types.InlineKeyboardButton(chat.name,
                                         callback_data=f"list_account_functions:{service_name}:chat:{chat.id}:{account_id}")
              for chat in chats]
        )

        if page_info["pages_num"] > 0:
            keyboard.add(types.InlineKeyboardButton(nav_buttons[0]['title'],
                                                    callback_data=f"list_account_functions:{service_name}:"
                                                                  f"{nav_buttons[0]['c_back']}"))

            keyboard.add(
                *[types.InlineKeyboardButton(button['title'],
                                             callback_data=f"list_account_functions:{service_name}:{button['c_back']}")
                  for button in nav_buttons[1:]]
            )

    for order in ['row', 'cell']:  # доб. кнопок, в зависимости от порядка (row - в ряд одна кнопка, cell - 2 в ряд)
        keyboard = get_ordered_buttons(keyboard, buttons, order, service_name)

    return keyboard


def get_ordered_buttons(keyboard, buttons, order, service_name) -> types.InlineKeyboardMarkup:
    cell_buttons = []

    for button in list(filter(lambda x: x['order'] == order, buttons)):
        btn_ = types.InlineKeyboardButton(button['title'],
                                          callback_data=f"list_account_functions:{service_name}:{button['c_back']}")

        if "service" in button and button["service"] == service_name or \
                "service" not in button:
            if order == 'cell':
                cell_buttons.append(btn_)
            else:
                keyboard.add(btn_)

    if order == 'cell':
        keyboard.add(*cell_buttons)

    return keyboard


def submit_delete_account(account_id):
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        types.InlineKeyboardButton('Да', callback_data=f"delete_account:yes:{account_id}"),
        types.InlineKeyboardButton('Нет', callback_data=f"delete_account:cancel")
    )

    return keyboard


def choose_posting_mode_kb(service_name, account_id=None, chat_id=0, is_multi_settings=0):
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        types.InlineKeyboardButton('Из избранного', callback_data=f"choose_posting_mode:favorite:{chat_id}:"
                                                                  f"{account_id}:{is_multi_settings}"),
        types.InlineKeyboardButton('Из канала/чата', callback_data=f"choose_posting_mode:manual:{chat_id}:"
                                                                   f"{account_id}:{is_multi_settings}"),
        types.InlineKeyboardButton('🔙 Назад', callback_data=f"list_tg_accounts:account:{service_name}:{account_id}")
    )

    return keyboard


def submit_post_kb(channel_id, post_id, account_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        types.InlineKeyboardButton('Да', callback_data=f"submit_post:yes:{channel_id}:{post_id}:{account_id}"),
        types.InlineKeyboardButton('Нет', callback_data=f"submit_post:cancel:{channel_id}:{post_id}:{account_id}")
    )

    return keyboard


def posting_settings_kb(account_id, config_, is_another_back_btn=False):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        {'title': f'Отправлять периодически', 'c_back': f"schedule:minutes"},
        {'title': f'Отправлять по времени', 'c_back': f"schedule:time"},
        {'title': f'{"✅" if config_.pin else "❌"} Отправка с закреплением', 'c_back': f"pin"},
        {'title': f'{"✅" if config_.notification else "❌"} Отправка с уведомлением', 'c_back': f"notification"},
        {'title': f'Удалить', 'c_back': f"delete"},
        {'title': f'Изменить источник', 'c_back': f"source"}
    ]

    keyboard.add(
        *[types.InlineKeyboardButton(button['title'],
                                     callback_data=f"posting_settings:{button['c_back']}:{account_id}:{config_.id}")
          for button in buttons]
    )

    if is_another_back_btn:
        back_button_callback = f"list_tg_accounts:account:auto_posting:{account_id}"
    else:
        back_button_callback = "back"

    keyboard.add(
        types.InlineKeyboardButton('⬅️ Назад', callback_data=back_button_callback)
    )

    return keyboard
