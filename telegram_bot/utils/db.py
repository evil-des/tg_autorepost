from sqlalchemy import Column, DateTime, String, Integer, create_engine, Float, Boolean, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,scoped_session
import datetime
from configparser import ConfigParser


config = ConfigParser()
config.read('config/config.ini')

engine = create_engine(
    f'{config["database"]["protocol"]}{config["database"]["host"]}'
)


session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
Base.query = session.query_property()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True)
    username = Column(String)
    fullname = Column(String)
    date_join = Column(DateTime, default=datetime.datetime.now())


class TelegramAccount(Base):
    __tablename__ = 'telegram_accounts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)

    chat_id = Column(BigInteger, unique=True)
    phone = Column(String, unique=True)
    username = Column(String)
    fullname = Column(String)
    password = Column(String)
    proxy = Column(String)

    answering_status = Column(Boolean, default=False)
    answering_text = Column(String, default=None)

    date_added = Column(DateTime, default=datetime.datetime.now())


class PostingConfig(Base):
    __tablename__ = 'posting_configs'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer)

    chat_id = Column(BigInteger)
    mode = Column(String)
    channel_id = Column(BigInteger)
    message_id = Column(BigInteger)
    pin = Column(Boolean, default=False)
    notification = Column(Boolean, default=False)
    schedule = Column(String, default="Не установлено")
    last_sent = Column(DateTime)


class MultiSettings(Base):
    __tablename__ = 'multi_settings'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer)

    mode = Column(String)
    channel_id = Column(BigInteger)
    message_id = Column(BigInteger)
    pin = Column(Boolean, default=False)
    notification = Column(Boolean, default=False)
    schedule = Column(String, default="Не установлено")


Base.metadata.create_all(bind=engine)
