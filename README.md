# Autorepost Telegram Bot
THis bot allows to use multiple telegram accounts in SMM purposes

## Installation
Install all dependencies:
```
pip install -r requirements.txt
```
1. Setup a database (default is PostgreSQL)
2. Configure the config file in this path: **telegram_bot/config/config.ini**

## Run
```
cd telegram_bot
python main/bot.py
python auth_bot/bot.py
```