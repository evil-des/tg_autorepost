from telegram_bot.utils.db import TelegramAccount, PostingConfig, session
import asyncio
import datetime
from telegram_bot.classes.TgAccount import TgAccount
import logging
from telebot import TeleBot
from telegram_bot.main.misc import config as project_config


async def posting():
    logging_bot = TeleBot(project_config["log_bot"]["token"], parse_mode="html")
    while True:
        configs = PostingConfig.query.filter(PostingConfig.schedule != "Не установлено").all()
        print(list(configs))
        for config in configs:
            account = TelegramAccount.query.filter(TelegramAccount.id == config.account_id).first()
            if len(config.schedule.split()) == 1 and config.schedule.isnumeric():
                if not config.last_sent or (
                        datetime.datetime.now() >=
                        config.last_sent +
                        datetime.timedelta(minutes=int(config.schedule))
                ):
                    await send_message(account, config, logging_bot)

        await asyncio.sleep(10)


async def send_message(account, config, logging_bot):
    tg_account = TgAccount(phone=account.phone)
    await tg_account.auth()

    try:
        await tg_account.forward_message(entity=config.chat_id, from_peer=config.channel_id,
                                         message_id=config.message_id,
                                         pin=config.pin, notification=config.notification)
        config.last_sent = datetime.datetime.now()
        session.commit()

        logging_bot.send_message(account.user.chat_id,
                                 tg_account.get_logging_text(config.channel_id,
                                                             config.message_id)
                                 )
    except Exception as e:
        logging_bot.send_message(account.user.chat_id,
                                 tg_account.get_logging_text(
                                     config.channel_id, config.message_id,
                                     status=False, error="\n".join(e.args))
                                 )
