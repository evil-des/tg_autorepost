
from aiogram import Bot, Dispatcher
from configparser import ConfigParser
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
# from filters.is_admin import IsAdmin

config = ConfigParser()
config.read('config/config.ini', encoding="utf8")

bot = Bot(token=config['bot']['token'], parse_mode='html')

storage = RedisStorage2()
dp = Dispatcher(bot, storage=storage)
# dp.filters_factory.bind(IsAdmin)
