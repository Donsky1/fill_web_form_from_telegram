import asyncio
import os
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
driver = webdriver.Chrome()


def send_value(element: str, value: str):
    """
    Задает значение для выбранного элемента поля html
    :param element: строка, input name
    :param value: строка, значение которое нужно установить в поле
    :return: 0
    """
    tmp = driver.find_element(By.NAME, element)
    tmp.clear()
    tmp.send_keys(value)


async def update_telegram_id(telegram_id):
    con = sqlite3.connect("form-users.db")  # open db or create db
    cur = con.cursor()  # get cursor to execute sql commands
    cur.execute(f'UPDATE users SET status = 1 WHERE telegram_id = ?', (telegram_id,))
    con.commit()
    cur.close()


async def update_capture_path(telegram_id, path):
    con = sqlite3.connect("form-users.db")  # open db or create db
    cur = con.cursor()  # get cursor to execute sql commands
    cur.execute(f'UPDATE users SET image_path = ? WHERE telegram_id = ?', (path, telegram_id))
    con.commit()
    cur.close()


async def selenium_request(url, line_from_db, user_id) -> None:
    driver.get(url)

    telegram_id = line_from_db[1]
    name = line_from_db[4]
    surname = line_from_db[5]
    email = line_from_db[6]
    phone = line_from_db[7]
    birthday = line_from_db[8].split('.')
    day = int(birthday[0])
    month_id = int(birthday[1])
    year = birthday[2]
    month_list = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь',
                  'Ноябрь', 'Декабрь']

    send_value('name', name)
    send_value('lastname', surname)

    btn = driver.find_element(By.XPATH,
                              '/html/body/main/div/section/div/div/div/div/div/div/div/div/div[2]/form/div[3]/div/button')
    btn.click()
    driver.implicitly_wait(1)
    send_value('email', email)
    send_value('phone', phone)
    btn = driver.find_element(By.XPATH,
                              '/html/body/main/div/section/div/div/div/div/div/div/div/div/div[2]/form/div[3]/div[2]/button')
    btn.click()
    driver.implicitly_wait(1)
    birthday = driver.find_element(By.XPATH,
                                   '/html/body/main/div/section/div/div/div/div/div/div/div/div/div[2]/form/div[2]/div/div/div/div/div[1]/input')
    birthday.click()
    birthday_select_month = Select(driver.find_element(By.XPATH,
                                                       '/html/body/main/div/section/div/div/div/div/div/div/div/div/div[2]/form/div[2]/div/div/div/div/div[2]/div/div[2]/div/div/header/div/div[1]/button/following-sibling::select'))

    birthday_select_month.select_by_visible_text(month_list[month_id-1])
    birthday_select_year = Select(driver.find_element(By.XPATH,
                                                      '/html/body/main/div/section/div/div/div/div/div/div/div/div/div[2]/form/div[2]/div/div/div/div/div[2]/div/div[2]/div/div/header/div/div[2]/button/following-sibling::select'))

    birthday_select_year.select_by_visible_text(year)

    for d in driver.find_elements(By.CLASS_NAME, 'vdpCellContent'):
        if d.text == str(day):
            d.find_element(By.XPATH, '..').click()
            break

    # last step
    btn = driver.find_element(By.XPATH,
                              '/html/body/main/div/section/div/div/div/div/div/div/div/div/div[2]/form/div[4]/div[2]/button')
    btn.click()
    await asyncio.sleep(3)
    data_save = datetime.datetime.now()
    capture_path = f'{data_save.strftime("%Y-%m-%d_%H-%M")}_{user_id}.png'
    driver.save_screenshot(capture_path)
    await update_telegram_id(telegram_id)
    await update_capture_path(telegram_id=telegram_id, path=capture_path)
    return
