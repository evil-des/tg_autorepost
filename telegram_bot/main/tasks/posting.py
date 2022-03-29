from telegram_bot.utils.db import TelegramAccount, PostingConfig, session
import asyncio
import datetime
from telegram_bot.classes.TgAccount import TgAccount
import logging


async def posting():
    while True:
        configs = PostingConfig.query.filter(PostingConfig.schedule != "Не установлено").all()
        print(list(configs))
        for config in configs:
            account = TelegramAccount.query.filter(TelegramAccount.id == config.account_id).first()

            if len(config.schedule.split()) == 1 and config.schedule.isnumeric():
                if not config.last_sent or (datetime.datetime.now() >=
                                            config.last_sent + datetime.timedelta(minutes=int(config.schedule))):
                    tg_account = TgAccount(phone=account.phone)
                    await tg_account.auth()

                    await tg_account.forward_message(entity=config.chat_id, from_peer=config.channel_id,
                                                     message_id=config.message_id,
                                                     pin=config.pin, notification=config.notification)
                    config.last_sent = datetime.datetime.now()
                    session.commit()
                    logging.info(f"[{account.phone}] Отправлено сообщение в канал!")

        await asyncio.sleep(10)

