import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot import asyncio_filters
import asyncio
import sqlite3
from pathlib import Path
import requests

from config import TOKEN
from req import selenium_request

BASE_DIR = Path(__file__).resolve().parent
con = sqlite3.connect("form-users.db")  # open db or create db
cur = con.cursor()  # get cursor to execute sql commands
# specially not looking on type data, for simplicity
cur.execute("CREATE TABLE  IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "telegram_id TEXT NOT NULL, "
            "telegram_user TEXT NOT NULL, "
            "status boolean NOT NULL default 0, "
            "name TEXT NOT NULL, "
            "surname TEXT NOT NULL, "
            "email TEXT NOT NULL, "
            "phone TEXT NOT NULL, "
            "birthday TEXT NOT NULL,"
            "image_path TEXT);")
cur.close()


# state, where we can save our user states in memory
class Form(StatesGroup):
    name = State()
    surname = State()
    email = State()
    phone = State()
    birthday = State()


state_storage = StateMemoryStorage()
bot = AsyncTeleBot(TOKEN, parse_mode='html', state_storage=state_storage)


# create async def to save data into db
async def insert_to_db(telegram_id, telegram_user, data):
    cur = con.cursor()  # get cursor to execute sql commands
    cur.execute(
        "INSERT INTO users (telegram_id, telegram_user, name, surname, email, phone, birthday) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (telegram_id, telegram_user, data['name'], data['surname'], data['email'], data['phone'], data['birthday']))
    con.commit()
    cur.close()


async def select_from_db():
    cur = con.cursor()  # get cursor to execute sql commands
    cur.execute("SELECT * FROM users where status = 0")
    result = cur.fetchall()
    cur.close()
    return result


async def fill_form():
    url = 'https://b24-iu5stq.bitrix24.site/backend_test/'
    while True:
        data = await select_from_db()
        if data:
            r = requests.get(url)
            if r.status_code == 200:
                for line in data:
                    user_id = line[0]
                    await selenium_request(url, line, user_id)
        await asyncio.sleep(20)


@bot.message_handler(commands=['start', 'help'])
async def start_menu(message):
    await bot.reply_to(message,
                       f'Добро пожаловать {message.from_user.first_name}, тебе необходимо заполнить информацию о себе.')


@bot.message_handler(commands=['go'])
async def message_hundler(message):
    """
    Here we are starting state name
    """
    markup = telebot.types.ForceReply(selective=False, input_field_placeholder='Вася')
    await bot.set_state(message.from_user.id, Form.name, message.chat.id)
    await bot.send_message(message.chat.id, 'Введите ваше имя', reply_markup=markup)


@bot.message_handler(commands='cancel')
async def any_state(message):
    """
    Cancel state
    """
    await bot.send_message(message.chat.id, "Фильтр был сброшен, повторите шаги заново")
    await bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(state=Form.name)
async def name_get(message):
    """
    State 1. Will process when user's state is Form.name.
    """
    markup = telebot.types.ForceReply(selective=False, input_field_placeholder='Пупкин')
    await bot.set_state(message.from_user.id, Form.surname, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = message.text
    await bot.send_message(message.chat.id, 'Введите вашу фамилию', reply_markup=markup)


@bot.message_handler(state=Form.surname)
async def surname_get(message):
    """
    State 2. Will process when user's state is Form.surname.
    """
    markup = telebot.types.ForceReply(selective=False, input_field_placeholder='test@test.ru')
    # skip email check
    await bot.set_state(message.from_user.id, Form.email, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['surname'] = message.text
    await bot.send_message(message.chat.id, 'Введите вашу почту по образцу', reply_markup=markup)


@bot.message_handler(state=Form.email)
async def email_get(message):
    """
    State 3. Will process when user's state is Form.email.
    """
    markup = telebot.types.ForceReply(selective=False, input_field_placeholder='+79090150215')
    # skip phone check
    await bot.set_state(message.from_user.id, Form.phone, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['email'] = message.text
    await bot.send_message(message.chat.id, 'Введите ваш номер телефона', reply_markup=markup)


@bot.message_handler(state=Form.phone)
async def phone_get(message):
    """
    State 4. Will process when user's state is Form.phone.
    """
    markup = telebot.types.ForceReply(selective=False, input_field_placeholder='22.02.2000')
    # skip birthday check
    await bot.set_state(message.from_user.id, Form.birthday, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['phone'] = message.text
    await bot.send_message(message.chat.id, 'Введите дату рождения, через точку (пример: 01.01.200)', reply_markup=markup)


@bot.message_handler(state=Form.birthday)
async def birthday_get(message):
    """
    State 5. Will process when user's state is Form.birthday.
    """
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['birthday'] = message.text

    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        await insert_to_db(message.from_user.id, message.from_user.first_name, data)  # save data into db
        await bot.send_message(message.chat.id,
                               "Ваши данные:\n<b>Имя: {name}\nФамилия: {surname}\nПочта: {email}\nТелефон: {phone}\nДень рождения: {birthday}</b>".format(
                                   name=data['name'], surname=data['surname'], email=data['email'], phone=data['phone'],
                                   birthday=data['birthday']))

    await bot.delete_state(message.from_user.id, message.chat.id)


if __name__ == '__main__':
    bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(fill_form()), loop.create_task(bot.polling())]
    wait_tasks = asyncio.wait(tasks)
    loop.run_until_complete(wait_tasks)
    loop.close()
