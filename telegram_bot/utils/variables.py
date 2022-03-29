# т.к. в aiogram.contrib.fsm_storage в методе get_data используется метод copy.deepcopy
# https://pythonworld.ru/moduli/modul-copy.html
tg_accounts = {}

CHATS_LIMIT = 30  # per page