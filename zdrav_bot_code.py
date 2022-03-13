# import xml.etree.ElementTree as ET
import json

import requests
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
import aiogram.utils.markdown as md
from aiogram.types import ParseMode

import config
import logging
from aiogram import Bot, Dispatcher, executor, types
import mis_arianda
import db_postgre as db

API_TOKEN = config.TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()  # TODO сюда БД
dp = Dispatcher(bot, storage=storage)


# START - НАЧАЛО ВЗАИМОДЕЙСТВИЯ С БОТОМ
@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
    await message.answer("Добро пожаловать, {0.first_name}!"
                         "".format(message.from_user, bot.get_me()),
                         parse_mode='html')

    with open("start_info_message.txt", 'r', encoding='utf8') as intro_f:
        await message.answer(intro_f.read())

    await lk_question(message)


# ToDo - кнопка НАЗАД
# def one_step_back():
#     keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
#     keyboard.add("НАЗАД")
#     return keyboard

# Главное меню
@dp.callback_query_handler(text="main_menu")
async def main_menu(call: types.CallbackQuery):
    main_markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("ЗАПИСАТЬСЯ", callback_data='record')
    item2 = types.InlineKeyboardButton("МОИ ЗАПИСИ", callback_data='my_recordings')
    item3 = types.InlineKeyboardButton("ШТРИХ-КОД", callback_data='entry_code')
    item4 = types.InlineKeyboardButton("ЗАКЛЮЧЕНИЯ", callback_data='doctor_res')
    main_markup.add(item1, item2, item3, item4)

    await call.message.answer("ГЛАВНОЕ МЕНЮ", reply_markup=main_markup)


async def lk_question(message: types.Message):
    lk_markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("ДА", callback_data='lk_exists')
    item2 = types.InlineKeyboardButton("НЕТ", callback_data='lk_not_exists')
    lk_markup.add(item1, item2)

    await message.answer("Есть ли у Вас личный кабинет?", reply_markup=lk_markup)

    # one_step_back()


''' ОТСЛЕЖИВАНИЕ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЯ И ОТРАБОТКА ЛОГИКИ НАЖАТИЯ КНОПОК '''
''' 1 - у пользователя нет ЛК: 1 шаг - текст про преимущества регистрации и 2 кнопки '''


@dp.callback_query_handler(text="lk_not_exists")
async def registration_offer(call: types.CallbackQuery):
    registration_question = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("Зарегистрироваться", callback_data='to_registration')
    item2 = types.InlineKeyboardButton("Продолжить без регистрации", callback_data='continue_without_reg')
    registration_question.add(item1, item2)

    await call.message.answer("Зарегистрировавшись, "
                              "Вы получите доступ к сервисам записи и оплаты. "
                              "А ещё наш бот пришлет напоминание за сутки до "
                              "приема и штрих-код для прохода на территорию "
                              "центра.", reply_markup=registration_question)
    # one_step_back()

    # bot.delete_message(msg.chat_id, msg.message_id)
    # bot.register_next_step_handler(msg, getg )


'''НАЖАТИЕ КНОПКИ ЗАРЕГИСТРИРОВАТЬСЯ - ОТПРАВКА ССЫЛКИ НА ФОРМУ РЕГИСТРАЦИИ'''


@dp.callback_query_handler(text="to_registration")
async def registration_link(call: types.CallbackQuery):
    await call.message.answer("Для регистрации перейдите по ссылке ниже на сайт СЗОНКЦ Соколова и заполните"
                              " форму регистрации.\n\n"
                              "🌐 https://med122.com/telemedicine/register/\n\n"
                              "После заполнения формы нашим операторам потребуется время"
                              " для обработки Ваших персональных данных.\n"
                              "Они с Вами свяжутся для подтверждения данных и вышлют на почту логин и пароль.\n\n"
                              "Среднее время создания личного кабинета: 1-2 рабочих дня.")
    await lk_question(call.message)


'''НАЖАТИЕ КНОПКИ ЗАРЕГИСТРИРОВАТЬСЯ - ОТПРАВКА ИНФОРМАЦИИ О ЦЕНТРЕ'''


@dp.callback_query_handler(text="continue_without_reg")
async def registration_link(call: types.CallbackQuery):
    record_btn = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("Записаться к врачу", callback_data='record_to_doc')
    record_btn.add(item1)
    with open("about_clinic.txt", 'r', encoding='utf8') as about_f:
        await call.message.answer(about_f.read(), reply_markup=record_btn)


'''НАЖАТИЕ КНОПКИ ЗАПИСАТЬСЯ К ВРАЧУ (НЕЗАРЕГ. ПОЛЬЗОВАТЕЛЬ) - ТЕКСТ И ПРЕДЛОЖЕНИЕ ЗАРЕГАТЬСЯ'''


@dp.callback_query_handler(text="record_to_doc")
async def registration_link(call: types.CallbackQuery):
    await call.message.answer("Запись к врачу через бота доступна "
                              "только зарегистрированным пользователям")

    await registration_offer(call)


# ToDo продолжить логику взаимодействия с неавторизированным пользователем - см. Bot userflow

''' 2 - у пользователя есть ЛК: переход к процессу авторизации (ввод логина и пароля)'''


# Используем состояния (States) для обработки введенных логина и пароля
class RegForm(StatesGroup):
    login = State()  # Задаем состояние
    passwd = State()


@dp.callback_query_handler(text="lk_exists")
async def authorisation_start(call: types.CallbackQuery):
    await RegForm.login.set()  # задаем state (состояние) ввода логина
    await call.message.answer("Введите логин: \n(тот же, что Вы используете для "
                              "доступа к личному кабинету на сайте lk.med122.com)")


@dp.message_handler(state=RegForm.login)
async def process_name(message: types.Message, state: FSMContext):
    #  Второй аргумент state типа FSMContext. Через него можно получить данные от FSM-бэкенда.
    async with state.proxy() as data:
        data['login'] = message.text  # сохраняем введенный пользователем логин
        await RegForm.next()  # переходим к следующему состоянию - у нас это ввод пароля
        await message.answer("Введите пароль:")
        await state.update_data(passwd=message.text)  # обновляем data и state для сохранения пароля


@dp.message_handler(state=RegForm.passwd)
async def process_passwd(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['passwd'] = message.text  # сохраняем введенный пароль
        await state.finish()

        # отправка POST-запроса с полученными логином и паролем для авторизации пользователя и получения токена
        # возможно, тут стоит что-то вынести отдельно именно для МИС Ариадна -- вынесено

        login_response = mis_arianda.auth(data['login'], data['passwd'])

        if login_response.json().get("success"):
            # если введены верные логин и пароль, то в ответ нам приходит токен для доступа к данным
            token = login_response.json().get("data").get("token")  # ToDo нужно сохранять токен в БД вместе с  chat_id
            db.save_token(message.chat.id, token)

            print("Authorization: SUCCESS!")
            print(db.use_token(message.chat.id))
            await auth_welcome(message)
            # get_info = mis_arianda.get_patient_info(db.use_token(message.chat.id))
            # patient_lastname = get_info.get("lastname")
            # patient_firstname = get_info.get("firstname")
            # patient_secondname = get_info.get("secondname")
            # print(patient_lastname + patient_secondname + patient_firstname)
            # await message.answer(f"Добро Пожаловать, {patient_firstname} {patient_secondname}!")
            # await message.answer("Вам доступны следующие сервисы:")

        else:
            await message.answer("Логин/пароль неверный, попробуйте ещё раз")
            await lk_question(message)


async def auth_welcome(message: types.Message):
    welcome_menu = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("ГЛАВНОЕ МЕНЮ", callback_data='main_menu')
    item2 = types.InlineKeyboardButton("Информация о клинике", callback_data='clinic_info')
    item3 = types.InlineKeyboardButton("Мои данные", callback_data='my_info')
    welcome_menu.add(item1, item2, item3)

    get_info = mis_arianda.get_patient_info(db.use_token(message.chat.id))
    patient_lastname = get_info.get("lastname")
    patient_firstname = get_info.get("firstname")
    patient_secondname = get_info.get("secondname")
    print(patient_lastname + patient_secondname + patient_firstname)
    await message.answer(f"Добро Пожаловать, {patient_firstname} {patient_secondname}!", reply_markup=welcome_menu)




''' 2.1 - сервис МОИ ЗАПИСИ '''


@dp.callback_query_handler(text="my_recordings")
async def registration_offer(call: types.CallbackQuery):
    cancel_rec_btn = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("Отменить запись", callback_data='cancel_recording')
    item2 = types.InlineKeyboardButton("ГЛАВНОЕ МЕНЮ", callback_data='main_menu')
    cancel_rec_btn.add(item1, item2)

    all_recordings = mis_arianda.get_recordings(db.use_token(call.message.chat.id))
    i = 0
    if all_recordings:
        for recording in all_recordings:
            i += 1
            await call.message.answer(f"Запись {i}:\n"
                                      f"Дата и время приёма: {recording.get('dat_bgn')}\n"
                                      f"Специалист: {recording.get('spec')}\n"
                                      f"ФИО врача: {recording.get('lastname')} "
                                      f"{recording.get('firstname')} {recording.get('secondname')}\n"
                                      f"Место: {recording.get('depname')}\n"
                                      f"Адрес: {recording.get('addr')}\n"
                                      f"Кабинет: {recording.get('cab')}\n"
                                      f"Телефон:  {recording.get('phone')}",
                                      reply_markup=cancel_rec_btn)
    else:
        to_main_menu = types.InlineKeyboardMarkup(row_width=1)
        item2 = types.InlineKeyboardButton("ГЛАВНОЕ МЕНЮ", callback_data='main_menu')
        to_main_menu.add(item2)
        await call.message.answer("У вас нет записей", reply_markup=to_main_menu)



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
