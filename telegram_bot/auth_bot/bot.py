
# Creator - TG -> @evildes

from aiogram import executor
from handlers import dp
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    # loop.create_taask()
    executor.start_polling(dp, skip_updates=True)
