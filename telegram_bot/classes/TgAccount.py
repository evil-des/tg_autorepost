from telethon import TelegramClient, events, types
from configparser import ConfigParser
from telegram_bot.utils.variables import tg_accounts
import logging
from telethon import functions
import asyncio
from telegram_bot.utils.db import TelegramAccount

config = ConfigParser()
config.read('config/config.ini', encoding="utf8")


class TgAccount:
    def __init__(self, phone=None, proxy=None):
        # self.user = User.query.filter(User.chat_id == chat_id).first()
        self.id = len(tg_accounts) + 1

        self.phone = phone
        self.password = None
        self.user_info = None

        self.client = None
        self.auto_answering = None
        self.sent_messages_ids = []

        # # добавление аккаунта в общий пулл сессий'
        session = list(filter(lambda x: x.get_phone() == self.phone, tg_accounts.values()))
        if session:
            self.client = session[0].client
            self.auto_answering = session[0].auto_answering
            self.sent_messages_ids = session[0].sent_messages_ids
            self.id = session[0].id
            logging.debug(self.client)
            logging.debug(self.auto_answering)
            logging.debug(f'got exist session of [{self.id}] account')
        else:
            # TODO proxy auth
            # connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
            self.client = TelegramClient(str(self.phone), int(config['auth_bot']['app_id']),
                                         config['auth_bot']['api_hash'])

        tg_accounts[self.id] = self

    def get_phone(self) -> str:
        """
        Получить поле Phone
        :return: phone number
        """
        return str(self.phone)

    async def get_message(self, chat_id, message_id):
        message = await self.client.get_messages(chat_id, message_id)
        return message

    async def get_message_by_link(self, link):
        chat, msg_id = link.split('https://t.me/')[-1].split('/')  # https://t.me/<chat>/<msg_id>
        chat = await self.client.get_entity(chat)
        message = await self.client.get_messages(chat, ids=int(msg_id))
        return message

    async def get_fav_message(self, chat_id):
        message = await self.client.get_messages(chat_id, limit=1)
        try:
            return message[-1]
        except Exception as e:
            return None

    async def forward_message(self, entity, from_peer, message_id, pin=False, notification=True):
        # await self.client.send_message(chat, message)
        await self.client.forward_messages(entity=entity, messages=message_id, from_peer=from_peer, silent=notification)
        if pin:
            await self.client.pin_message(entity, message_id, notify=notification)

    async def auth(self, code=None, password=None) -> None:
        """
        Авторизовать аккаунт
        :param code: код, пришедший из смс
        :param password: пароль от 2fa
        :return: None
        """
        await self.connect()
        self.password = password

        if password and code:
            await self.client.sign_in(self.phone, code, password=self.password)
        elif password and not code:
            await self.client.sign_in(self.phone, password=self.password)
        elif code:
            await self.client.sign_in(self.phone, code)
        else:
            await self.client.sign_in(self.phone)

    async def send_code_request(self) -> None:
        """
        Отрпавить код для авторизации
        :return: None
        """
        await self.connect()
        await self.client.send_code_request(self.phone)

    async def get_user_info(self) -> dict:
        """
        Получить информацию об аккаунте
        :return: user information (dict)
        """
        if not self.user_info:
            await self.connect()
            user = await self.client.get_me()
            self.user_info = {
                "username": user.username,
                "chat_id": user.id,
                "fullname": f"{user.first_name} {user.last_name}"
            }
        return self.user_info

    async def connect(self) -> None:
        """
        Подключить аккаунт к серверам Telegram
        :return: None
        """
        if not self.client.is_connected():
            try:
                await self.client.connect()
            except Exception as e:
                await self.auth()

    async def disconnect(self) -> None:
        """
        Отключить аккаунт от серверов Telegram
        :return: None
        """
        if self.client.is_connected():
            await self.client.disconnect()

    async def get_chats(self) -> list:
        """
        Получить список всех диалогов аккаунта
        :return: list of accounts
        """
        chats = await self.client.get_dialogs()
        return list(filter(lambda x: x.is_group or x.is_channel, chats))

    async def stop(self) -> None:
        """
        Завершает работу аккаунта и убирает из общего пула сессий
        :return: None
        """
        await self.client.disconnect()
        del tg_accounts[self.id]

    async def start_auto_answering(self) -> None:
        """
        Начать работу автоответчика
        :return: None
        """
        if not self.auto_answering:
            self.client.add_event_handler(self.new_message,
                                          events.NewMessage(incoming=True))
            await self.connect()
            self.auto_answering = asyncio.create_task(self.client.run_until_disconnected())

    async def stop_auto_answering(self) -> None:
        """
        Остановить работу автоответчика
        :return: None
        """
        if self.auto_answering:
            await self.disconnect()
            self.auto_answering.cancel()
            logging.debug(f'Stopped auto_answering for [{self.id}] account')

    async def new_message(self, event: events.newmessage.NewMessage.Event) -> None:
        """
        Обработчик новых входящих сообщений
        :param event:
        :return: None
        """
        account = TelegramAccount.query.filter(TelegramAccount.phone == self.phone).first()
        if await self.is_new_chat(event.chat_id):
            await event.reply(account.answering_text)
            self.sent_messages_ids.append(event.chat_id)

    async def is_new_chat(self, chat_id) -> bool:
        """
        Проверить чат на уникальность
        :param chat_id:
        :return:
        """
        # await self.get_user_info()
        # messages = await self.client.get_messages(chat, limit=30)
        # if not messages or self.user_info['chat_id'] not in [x.chat.id for x in messages]:
        #     return True
        if chat_id not in self.sent_messages_ids:
            return True
        return False

    async def check_chat_invite_request(self, invite):
        result = await self.client(functions.messages.CheckChatInviteRequest(
            hash=invite
        ))
        return result

    async def join_chat(self, entity, is_private: bool = False):
        if not is_private:
            updates = await self.client(
                functions.channels.JoinChannelRequest(entity)
            )
        else:
            updates = await self.client(
                functions.messages.ImportChatInviteRequest(entity)
            )
        return updates
