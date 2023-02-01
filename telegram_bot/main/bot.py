
# Creator - TG -> @evildes

from aiogram import executor
from handlers import dp
import logging
import asyncio
from telegram_bot.main.tasks.posting import posting
from telegram_bot.utils.db import session

logging.basicConfig(level=logging.DEBUG)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(posting())

    executor.start_polling(dp, skip_updates=True)
    # session.close()
