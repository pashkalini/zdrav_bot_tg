# import xml.etree.ElementTree as ET
import datetime

import requests
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import ParseMode
from aiogram.utils.callback_data import CallbackData

import config
import logging
from aiogram import Bot, Dispatcher, executor, types
import mis_arianda
import db_postgre as db

API_TOKEN = config.TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()  # TODO сюда БД
dp = Dispatcher(bot, storage=storage)

msg_ids_from_auth = []


# START - НАЧАЛО ВЗАИМОДЕЙСТВИЯ С БОТОМ
@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
    await message.answer("Добро пожаловать, {0.first_name}!"
                         "".format(message.from_user),
                         parse_mode='html')

    with open("start_info_message.txt", 'r', encoding='utf8') as intro_f:
        await message.answer(intro_f.read())

    await lk_question(message)


# вопрос к пользователю про существование ЛК
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
    await call.message.delete()  # удаление предыдущего сообщения
    # await call.message.delete_reply_markup()  # удаление кнопок от предыдущего сообщения

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
    # await call.message.delete_reply_markup()  # удаление кнопок у предыдущего сообщения
    await call.message.delete()  # удаление предыдущего сообщения

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
    # await call.message.delete_reply_markup()  # удаление кнопок у предыдущего сообщения
    await call.message.delete()  # удаление предыдущего сообщения

    record_btn = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("Записаться к врачу", callback_data='record_to_doc')
    record_btn.add(item1)
    with open("about_clinic.txt", 'r', encoding='utf8') as about_f:
        await call.message.answer(about_f.read(), reply_markup=record_btn)


'''НАЖАТИЕ КНОПКИ ЗАПИСАТЬСЯ К ВРАЧУ (НЕЗАРЕГ. ПОЛЬЗОВАТЕЛЬ) - ТЕКСТ И ПРЕДЛОЖЕНИЕ ЗАРЕГАТЬСЯ'''


@dp.callback_query_handler(text="record_to_doc")
async def registration_link(call: types.CallbackQuery):
    await call.message.delete_reply_markup()  # удаление кнопок у предыдущего сообщения

    await call.message.answer("Запись к врачу через бота доступна "
                              "только зарегистрированным пользователям")

    await registration_offer(call)


''' 2 - у пользователя есть ЛК: переход к процессу авторизации (ввод логина и пароля)'''


#  повторная авторизация
async def repeat_auth(message: types.Message, method):
    if method == "error":
        # await message.delete()
        markup = types.InlineKeyboardMarkup(row_width=1)
        item = types.InlineKeyboardButton("Авторизоваться 🔐", callback_data='lk_exists')
        item2 = types.InlineKeyboardButton("Продолжить без авторизации", callback_data='lk_not_exists')
        markup.add(item, item2)

        await message.edit_text(text="Вас давно не было. Для продолжения использования всех сервисов "
                                     "необходимо повторно войти в личный кабинет.", reply_markup=markup)
        return "Повторная авторизация"
    else:
        return


# Используем состояния (States) для обработки введенных логина и пароля
class RegForm(StatesGroup):
    login = State()  # Задаем состояние
    passwd = State()


#  переход к процессу авторизации при нажатии на конпку с callback_data = lk_exists
@dp.callback_query_handler(text="lk_exists")
async def authorisation_start(call: types.CallbackQuery):
    # await call.message.delete()  # удаление предыдущего сообщения

    await RegForm.login.set()  # задаем state (состояние) ввода логина
    message_id = await call.message.edit_text("Введите логин: \n(тот же, что Вы используете для "
                                              "доступа к личному кабинету на сайте lk.med122.com)")
    msg_ids_from_auth.append(message_id)  # сохраняем id сообщения для последующего удаления, см. ф-цию auth_welcome


#  в состоянии 1 берем логин
@dp.message_handler(state=RegForm.login)
async def process_name(message: types.Message, state: FSMContext):
    await message.delete()  # # чудо-удаление логина
    #  Второй аргумент state типа FSMContext. Через него можно получить данные от FSM-бэкенда.
    async with state.proxy() as data:
        data['login'] = message.text  # сохраняем введенный пользователем логин
        await RegForm.next()  # переходим к следующему состоянию - у нас это ввод пароля

        message_id = await message.answer("Введите пароль:")
        msg_ids_from_auth.append(message_id)  # сохраняем id сообщения для последующего удаления, см. ф-цию auth_welcome
        await state.update_data(passwd=message.text)  # обновляем data и state для сохранения пароля


# в состоянии 2 берем пароль
@dp.message_handler(state=RegForm.passwd)
async def process_passwd(message: types.Message, state: FSMContext):
    await message.delete()  # чудо-удаление пароля
    async with state.proxy() as data:
        data['passwd'] = message.text  # сохраняем введенный пароль
        await state.finish()

        # отправка POST-запроса с полученными логином и паролем для авторизации пользователя и получения токена
        # возможно, тут стоит что-то вынести отдельно именно для МИС Ариадна -- вынесено

        login_response = mis_arianda.auth(data['login'], data['passwd'])

        if login_response.json().get("success"):
            # если введены верные логин и пароль, то в ответ нам приходит токен для доступа к данным
            token = login_response.json().get("data").get("token")
            db.save_token(message.chat.id, token)  # сохраняем токен в БД вместе с chat_id

            print("Authorization: SUCCESS!")
            # print(db.use_token(message.chat.id))

            welcome_menu = types.InlineKeyboardMarkup(row_width=1)
            item1 = types.InlineKeyboardButton("В личный кабинет ➡", callback_data='lk_menu')
            welcome_menu.add(item1)
            await message.answer("Добро пожаловать!\n\n", reply_markup=welcome_menu)
            # "⚠ В целях безопасности рекомендуем Вам удалить из чата сообщения с "
            # "логином и паролем от личного кабинета."
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


'''2.0. - стартовое меню = личный кабинет'''

# callback item для кнопки ГЛАВНОЕ МЕНЮ (встречается много раза, поэтому выносим)
main_menu_item = types.InlineKeyboardButton("ГЛАВНОЕ МЕНЮ", callback_data='main_menu')


@dp.callback_query_handler(text="lk_rest")
async def restart_welcome(call: types.CallbackQuery):
    await call.message.delete()
    await lk_question(call.message)


# СТАРТОВОЕ МЕНЮ
@dp.callback_query_handler(text="lk_menu")
async def auth_welcome(call: types.CallbackQuery):
    #  повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, mis_arianda.get_patient_info(db.use_token(call.message.chat.id)))

    if rep_auth == "Повторная авторизация":
        return
    else:
        welcome_menu = types.InlineKeyboardMarkup(row_width=1)
        # item1 = types.InlineKeyboardButton("ГЛАВНОЕ МЕНЮ", callback_data='main_menu')
        item2 = types.InlineKeyboardButton("Информация о клинике", callback_data='clinic_info')
        item3 = types.InlineKeyboardButton("Мои данные", callback_data='my_info')
        item4 = types.InlineKeyboardButton("Оставить отзыв ✍", callback_data='feedback')
        item5 = types.InlineKeyboardButton("Выйти 🚪", callback_data='lk_rest')
        welcome_menu.add(main_menu_item, item2, item3, item4, item5)

        # TODO возникает ошибка "Message can't be deleted for everyone" при повторной авторизации - не удаляются
        #  сообщения и не пройти дальше в личный кабинет из-за этого
        if msg_ids_from_auth:  # удаление сообщений о вводе логина и пароля
            for msg_id in msg_ids_from_auth:
                # print(msg_id)
                await bot.delete_message(chat_id=call.message.chat.id, message_id=msg_id.message_id)
            msg_ids_from_auth.clear()

        get_info = mis_arianda.get_patient_info(db.use_token(call.message.chat.id))
        patient_lastname = get_info.get("lastname")
        patient_firstname = get_info.get("firstname")
        patient_secondname = get_info.get("secondname")
        print(patient_lastname + patient_secondname + patient_firstname)
        await call.message.edit_text(
            f"<b>Личный кабинет:</b> {patient_firstname} {patient_secondname} {patient_lastname}",
            reply_markup=welcome_menu)


'''2.0.0. - стартовое меню -> главное меню '''


# Главное меню
@dp.callback_query_handler(text="main_menu")
async def main_menu(call: types.CallbackQuery):
    await call.answer()
    main_markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("ЗАПИСАТЬСЯ", callback_data='record')
    item2 = types.InlineKeyboardButton("МОИ ЗАПИСИ", callback_data='my_recordings')
    item3 = types.InlineKeyboardButton("ШТРИХ-КОД", callback_data='entry_code')
    item4 = types.InlineKeyboardButton("ЗАКЛЮЧЕНИЯ", callback_data='doctor_res')
    item5 = types.InlineKeyboardButton("Личный кабинет", callback_data='lk_menu')
    main_markup.add(item1, item2, item3, item4, item5)

    if msg_ids_from_my_recordings:  # удаление сообщений в сервисе МОИ ЗАПИСИ по id, если таковые имеются
        for msg_id in msg_ids_from_my_recordings:
            await bot.delete_message(chat_id=call.message.chat.id, message_id=msg_id.message_id)
        msg_ids_from_my_recordings.clear()

    await call.message.edit_text("📄 ГЛАВНОЕ МЕНЮ", reply_markup=main_markup)

    # await call.message.edit_reply_markup(main_markup)   # изменения кнопок без отправки нового сообщения


'''2.0.1. - стартовое меню -> о клинике '''


#  раздел О КЛИНИКЕ
@dp.callback_query_handler(text="clinic_info")
async def about_clinic(call: types.CallbackQuery):
    back_btn = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("Назад ↩", callback_data='lk_menu')
    back_btn.add(item1)
    with open("about_clinic.txt", 'r', encoding='utf8') as about_f:
        await call.message.edit_text(about_f.read(), reply_markup=back_btn)


'''2.0.2. - стартовое меню -> мои данные '''


#  раздел МОИ ДАННЫЕ
@dp.callback_query_handler(text="my_info")
async def patient_info(call: types.CallbackQuery):
    get_info = mis_arianda.get_patient_info(db.use_token(call.message.chat.id))
    #  повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, get_info)
    if rep_auth == "Повторная авторизация":
        return

    else:
        back_btn = types.InlineKeyboardMarkup(row_width=1)
        item1 = types.InlineKeyboardButton("Назад ↩", callback_data='lk_menu')
        back_btn.add(item1)

        await call.message.edit_text(f"<b>ФИО:</b> {get_info.get('lastname')} {get_info.get('firstname')} "
                                     f"{get_info.get('secondname')}\n"
                                     f"<b>Дата рождения:</b> {get_info.get('birthdatestr')}\n"
                                     f"<b>Телефон:</b> {get_info.get('phone')}\n"
                                     f"<b>Моб. телефон:</b> {get_info.get('cellular')}\n"
                                     f"<b>E-mail:</b> {get_info.get('email')}\n"
                                     f"<b>СНИЛС:</b> {get_info.get('snils')}\n"
                                     f"<b>Адрес:</b> {get_info.get('address_proj')}",
                                     reply_markup=back_btn)


'''2.0.3. - стартовое меню -> оставить отзыв '''


#  раздел ОСТАВИТЬ ОТЗЫВ
# Используем состояния (States) для обработки отзыва пользователя
class Feedback(StatesGroup):
    feedback = State()  # Задаем состояние
    end = State()


@dp.callback_query_handler(text="feedback")
async def get_feedback(call: types.CallbackQuery):
    await Feedback.feedback.set()  # задаем state (состояние) ввода логина
    await call.message.edit_text("Спасибо Вам за использование нашего чат-бота!\n\nЧтобы он становился лучше, "
                                 "напишите свои пожелания и замечания одним сообщением.")


@dp.message_handler(state=Feedback.feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['feedback_text'] = message.text  # сохраняем введенный пользователем отзыв
        await state.finish()

        get_info = mis_arianda.get_patient_info(db.use_token(message.chat.id))

        requests.get('https://api.telegram.org/bot{}/sendMessage'.format(config.TOKEN), params=dict(
            chat_id='@med122_feedback',
            text=f"{get_info.get('lastname')} {get_info.get('firstname')} "
                 f"{get_info.get('secondname')} (@{message.from_user.username}, {get_info.get('cellular')}) "
                 f"оставил отзыв: {data['feedback_text']}"
        ))

        back_btn = types.InlineKeyboardMarkup(row_width=1)
        item1 = types.InlineKeyboardButton("Назад ↩", callback_data='lk_menu')
        back_btn.add(item1)

        await message.answer("Спасибо! Мы обязательно учтём Ваше мнение.", reply_markup=back_btn)


''' 2.1. - главное меню -> сервис МОИ ЗАПИСИ '''

msg_ids_from_my_recordings = []


# сервис МОИ ЗАПИСИ - список записей
@dp.callback_query_handler(text="my_recordings")
async def recordings(call: types.CallbackQuery):
    await call.answer()
    # await call.message.delete()  # удаление предыдущего сообщения
    all_recordings = mis_arianda.get_recordings(db.use_token(call.message.chat.id))
    #  повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_recordings)

    if rep_auth == "Повторная авторизация":
        return
    else:
        cancel_rec_btn = types.InlineKeyboardMarkup(row_width=1)
        cancel_rec_menu_btn = types.InlineKeyboardMarkup(row_width=1)
        item1 = types.InlineKeyboardButton("❌ Отменить запись", callback_data='cancel_recording')
        # item2 = types.InlineKeyboardButton("ГЛАВНОЕ МЕНЮ", callback_data='main_menu')
        cancel_rec_btn.add(item1)
        cancel_rec_menu_btn.add(item1, main_menu_item)

        i = 0
        my_rec = []

        if all_recordings:
            for recording in all_recordings:
                i += 1
                recording_data = (f"<b>Запись №{i}:</b>\n"
                                  f"📅 {recording.get('dat_bgn')}\n"
                                  f"🩺️ {recording.get('spec')}\n"
                                  f"👨‍⚕ {recording.get('lastname')} "
                                  f"{recording.get('firstname')} {recording.get('secondname')}\n"
                                  f"🏥 {recording.get('depname')}\n"
                                  f"📍 {recording.get('addr')}\n"
                                  f"Кабинет: {recording.get('cab')}\n"
                                  f"☎ {recording.get('phone')}")
                my_rec.append(recording_data)
                # показываем записи к врачам
                # if recording == all_recordings[-1]:  # если запись последняя, то прикрепляем еще кнопку ГЛАВНОЕ МЕНЮ
            await call.message.edit_text("<b><u>МОИ ЗАПИСИ</u></b>\n\n" + '\n\n'.join(my_rec),
                                         reply_markup=cancel_rec_menu_btn)
            # else:
            #     message_id = await call.message.answer(recording_data, reply_markup=cancel_rec_btn)
            #     msg_ids_from_my_recordings.append(message_id)

        else:  # обработка случая, если нет записей
            to_main_menu = types.InlineKeyboardMarkup(row_width=1)
            to_main_menu.add(main_menu_item)
            await call.message.answer("У вас нет записей", reply_markup=to_main_menu)


# recs_rnumb_ids = []
# используем фабрику коллбэков (дальше тоже пригодится)
rnumb_cb = CallbackData("cancel", "rnumb_id")


# сервис МОИ ЗАПИСИ - отмена записи
@dp.callback_query_handler(text="cancel_recording")
async def canc_rec(call: types.CallbackQuery):
    all_recordings = mis_arianda.get_recordings(db.use_token(call.message.chat.id))
    #  повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_recordings)
    if rep_auth == "Повторная авторизация":
        return

    else:
        i = 0
        recs = types.InlineKeyboardMarkup(row_width=1)
        item1 = types.InlineKeyboardButton("↩ Назад", callback_data='my_recordings')

        for recording in all_recordings:
            i += 1
            rnumb = recording.get('rnumb_id')
            # canc_rnumb = f"cancel{rnumb}"
            # print(rnumb)
            # добавляем в цикле необходимое кол-во кнопок с callback_data равной id записи
            # item = types.InlineKeyboardButton(f"Отменить запись №{i}", callback_data=canc_rnumb)
            item = types.InlineKeyboardButton(f"Отменить запись №{i}", callback_data=rnumb_cb.new(rnumb_id=rnumb))
            # recs_rnumb_ids.append(rnumb)
            recs.add(item)

        recs.add(item1)
        await call.message.edit_reply_markup(reply_markup=recs)


#  обрабатываем кнопку с отменой записи, отменить запись по конкретному id из фабрики коллбэков rnumb_cb
# @dp.callback_query_handler(lambda c: c.data and c.data.startswith('cancel'))
@dp.callback_query_handler(rnumb_cb.filter())
async def canc_rec2(call: types.CallbackQuery, callback_data: dict):
    to_menu_btn = types.InlineKeyboardMarkup(row_width=1)
    # item = types.InlineKeyboardButton("ГЛАВНОЕ МЕНЮ", callback_data='main_menu')
    to_menu_btn.add(main_menu_item)
    # print(call.data.strip('cancel'))
    # mis_arianda.cancel_rec(db.use_token(call.message.chat.id), call.data.strip('cancel'))
    mis_arianda.cancel_rec(db.use_token(call.message.chat.id), callback_data['rnumb_id'])
    await call.message.edit_text(f"Запись отменена ❌", reply_markup=to_menu_btn)


''' 2.2. - главное меню -> сервис ЗАПИСАТЬСЯ '''

# используем фабрику коллбэков для передачи id специальности
rnumb_spec_cb = CallbackData("spec", "spec_id")


# 1. список специальностей
@dp.callback_query_handler(text="record")
async def show_spec_list(call: types.CallbackQuery):
    # await call.message.delete()  # удаление предыдущего сообщения
    all_spec = mis_arianda.get_spec_list(db.use_token(call.message.chat.id))
    #  повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_spec)

    if rep_auth == "Повторная авторизация":
        return
    else:
        spec_list_menu = types.InlineKeyboardMarkup(row_width=1)
        back_btn = types.InlineKeyboardButton("↩ Назад", callback_data='main_menu')

        for spec in all_spec:
            spec_id = spec.get('spec_id')
            # print(spec_id)
            spec_text = spec.get('spec_text')
            # добавляем в цикле необходимое кол-во кнопок с callback_data равной id специальности
            spec_item = types.InlineKeyboardButton(spec_text, callback_data=rnumb_spec_cb.new(spec_id=spec_id))
            spec_list_menu.add(spec_item)

        spec_list_menu.add(back_btn)
        await call.message.edit_text("🩺 Выберите специализацию врача", reply_markup=spec_list_menu)


# используем фабрику коллбэков для передачи id доктора и специальности
rnumb_doc_cb = CallbackData("spec", "spec_id", "doc_id")


# 2. список врачей
@dp.callback_query_handler(rnumb_spec_cb.filter())
async def show_doc_list(call: types.CallbackQuery, callback_data: dict):
    await call.answer(text="Идёт загрузка ⏳\nПожалуйста, подождите...", show_alert=True)
    all_doc = mis_arianda.get_doc_list(db.use_token(call.message.chat.id), callback_data['spec_id'])
    # повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_doc)
    if rep_auth == "Повторная авторизация":
        return

    else:
        doc_list_menu = types.InlineKeyboardMarkup(row_width=1)
        back_btn = types.InlineKeyboardButton("↩ Назад", callback_data='record')
        # используем нажатое-переданное spec_id для показа врачей
        all_doc = mis_arianda.get_doc_list(db.use_token(call.message.chat.id), callback_data['spec_id'])

        for doc in all_doc:
            doc_id = doc.get('doc_id')
            # print(spec_id)
            doc_name = f"{doc.get('doc_l_name')} {doc.get('doc_f_name')} {doc.get('doc_s_name')}"
            # добавляем в цикле необходимое кол-во кнопок с callback_data равной id специальности и id врача
            doc_item = types.InlineKeyboardButton(doc_name, callback_data=rnumb_doc_cb.new(
                spec_id=callback_data['spec_id'],
                doc_id=doc_id))
            doc_list_menu.add(doc_item)

        doc_list_menu.add(back_btn)
        await call.message.edit_text("👨‍⚕️Выберите врача", reply_markup=doc_list_menu)

# используем фабрику коллбэков для передачи id специальности, доктора и даты приема
rnumb_date_cb = CallbackData("spec", "spec_id", "doc_id", "date")


# 3. список номерков - выбор даты
@dp.callback_query_handler(rnumb_doc_cb.filter())
async def show_date_list(call: types.CallbackQuery, callback_data: dict):
    await call.answer()
    all_date = mis_arianda.get_rnumb_list(db.use_token(call.message.chat.id),
                                          callback_data['spec_id'], callback_data['doc_id'])
    # повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_date)
    if rep_auth == "Повторная авторизация":
        return

    else:
        date_list_menu = types.InlineKeyboardMarkup(row_width=3)
        back_btn = types.InlineKeyboardButton("↩ Назад",
                                              callback_data=f"spec:{callback_data['spec_id']}")
        # используем нажатое-переданное spec_id и doc_id для показа даты
        dates = []

        for date in all_date:
            f_date = date.get('rnumb_dat_begin').split(" ")[0]  # дата
            # print(f_date)
            ff_date = datetime.datetime.strptime(f_date, '%d.%m.%Y')
            today = datetime.datetime.today()
            # print(ff_date)
            # print("today: " + str(today))
            # print (today + datetime.timedelta(days=14))

            if ff_date < (today + datetime.timedelta(days=14)) and f_date not in dates:
                # datetime.isoweekday(now)
                # добавляем в цикле необходимое кол-во кнопок с callback_data равной id специальности, id врача и дату
                date_item = types.InlineKeyboardButton(f_date, callback_data=rnumb_date_cb.new(
                    spec_id=callback_data['spec_id'],
                    doc_id=callback_data['doc_id'],
                    date=f_date))
                date_list_menu.add(date_item)
                dates.append(f_date)

        date_list_menu.add(back_btn)
        await call.message.edit_text("📆 Выберите удобный день приема", reply_markup=date_list_menu)


rnumb_rec_id_cb = CallbackData('rec', 'rec_rnumb_id')


# 4. список номерков - выбор времени
@dp.callback_query_handler(rnumb_date_cb.filter())
async def show_time_list(call: types.CallbackQuery, callback_data: dict):
    await call.answer()
    all_date = mis_arianda.get_rnumb_list(db.use_token(call.message.chat.id),
                                          callback_data['spec_id'], callback_data['doc_id'])
    # повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_date)

    if rep_auth == "Повторная авторизация":
        return
    else:
        time_list_menu = types.InlineKeyboardMarkup(row_width=3)
        back_btn = types.InlineKeyboardButton("↩ Назад",
                                              callback_data=f"spec:{callback_data['spec_id']}:{callback_data['doc_id']}")
        times = []

        for date in all_date:
            f_date = date.get('rnumb_dat_begin').split(" ")[0]  # дата
            f_time = date.get('rnumb_dat_begin').split(" ")[1]  # время начала
            f_time_end = date.get('rnumb_dat_end').split(" ")[1]  # время окончания

            if f_date == callback_data['date'] and f_time not in times:
                time_item = types.InlineKeyboardButton(f"{f_time}-{f_time_end}", callback_data=rnumb_rec_id_cb.new(
                    rec_rnumb_id=date.get('rnumb_id')))
                time_list_menu.add(time_item)
                times.append(f_time)

        time_list_menu.add(back_btn)
        await call.message.edit_text("⏰ Выберите удобное время приема", reply_markup=time_list_menu)

# используем фабрику коллбэков для передачи id талона
rnumb_create_rec_cb = CallbackData('create_rec', 'rnumb_id')


# 5. подтверждение записи - инфо о талоне
@dp.callback_query_handler(rnumb_rec_id_cb.filter())
async def rec_confirmation(call: types.CallbackQuery, callback_data: dict):
    await call.answer()
    all_date = mis_arianda.get_rnumb_info(db.use_token(call.message.chat.id), callback_data['rec_rnumb_id'])
    # повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_date)

    if rep_auth == "Повторная авторизация":
        return
    else:
        confirm_rec = types.InlineKeyboardMarkup(row_width=3)
        confirm_btn = types.InlineKeyboardButton("✅ Записаться",
                                                 callback_data=rnumb_create_rec_cb.new(
                                                     rnumb_id=callback_data['rec_rnumb_id']))
        cancel_btn = types.InlineKeyboardButton("❌ Отмена", callback_data='main_menu')
        confirm_rec.add(confirm_btn, cancel_btn)

        for date in all_date:
            rec_info = (f"<b>Подтвердите запись:</b>\n"
                        f"📅 {date.get('rnumb_dat_begin')}-{date.get('rnumb_dat_end').split(' ')[1]}\n"
                        f"🩺️ {date.get('rnumb_spec')}\n"
                        f"👨‍⚕ {date.get('rnumb_doc_lname')} "
                        f"{date.get('rnumb_doc_fname')} {date.get('rnumb_doc_sname')}\n"
                        f"🏥 {date.get('rnumb_depname')}\n"
                        f"📍 {date.get('rnumb_addr')}\n"
                        f"Кабинет: {date.get('rnumb_cab')}\n"
                        f"☎ {date.get('rnumb_phone')}")

            await call.message.edit_text(rec_info, reply_markup=confirm_rec)


# 6. подтверждение записи - запись на талон + оплата
@dp.callback_query_handler(rnumb_create_rec_cb.filter())
async def create_recording(call: types.CallbackQuery, callback_data: dict):
    await call.answer()
    all_date = mis_arianda.create_rec(db.use_token(call.message.chat.id), callback_data['rnumb_id']).json()
    # повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_date)

    if rep_auth == "Повторная авторизация":
        return
    else:
        # TODO настроить оплату
        payment_menu = types.InlineKeyboardMarkup(row_width=3)
        pay_btn = types.InlineKeyboardButton("💳 Оплатить", callback_data="to_pay")
        cancel_btn = types.InlineKeyboardButton("❌ Отмена", callback_data='main_menu')
        payment_menu.add(pay_btn, cancel_btn)
        await call.message.edit_text("У Вас есть 15 минут для оплаты, иначе запись будет автоматически отменена.",
                                     reply_markup=payment_menu)


@dp.callback_query_handler(text="to_pay")
async def payment_confirmation(call: types.CallbackQuery):
    to_main_menu = types.InlineKeyboardMarkup(row_width=1)
    to_main_menu.add(main_menu_item)

    await call.message.edit_text('✅ <b>Оплата прошла успешно, запись подтверждена.</b>\n\n'
                                 'Свои записи Вы можете найти в ГЛАВНОЕ МЕНЮ->МОИ ЗАПИСИ.\n\n'
                                 'За сутки до приёма вы получите напоминание о приеме и штрих-код для входа. '
                                 'Он также будет находится в ГЛАВНОЕ МЕНЮ->ШТРИХ-КОД НА ВХОД.',
                                 reply_markup=to_main_menu)


''' 2.3. - главное меню -> сервис Заключения '''

# используем фабрику коллбэков для передачи
visit_history_cb = CallbackData('visit', 'visit_id', 'visit_tp', 'visit_date')

# 1. список посещений
@dp.callback_query_handler(text="doctor_res")
async def show_history(call: types.CallbackQuery):
    await call.answer(text="Идёт загрузка ⏳\nПожалуйста, подождите...", show_alert=True)
    all_visits = mis_arianda.get_history_list(db.use_token(call.message.chat.id))
    #  повторная авторизация, если необходимо
    rep_auth = await repeat_auth(call.message, all_visits)

    if rep_auth == "Повторная авторизация":
        return
    else:
        visit_list_menu = types.InlineKeyboardMarkup(row_width=1)
        back_btn = types.InlineKeyboardButton("↩ Назад", callback_data='main_menu')

        for visit in all_visits[:10]:
            visit_id = visit.get('keyid')
            visit_date = visit.get('dat').split(" ")[0]
            visit_spec = visit.get('spec')
            visit_tp = visit.get('typehistory')
            # добавляем в цикле необходимое кол-во кнопок с callback_data равной key_id = id посещения
            visit_item = types.InlineKeyboardButton(f'📋 {visit_date}, {visit_spec}',
                                                   callback_data=visit_history_cb.new(visit_id=visit_id, visit_tp=visit_tp,
                                                                                      visit_date=visit_date))
            visit_list_menu.add(visit_item)

        visit_list_menu.add(back_btn)

        await call.message.edit_text("<b><u>МОИ ПОСЕЩЕНИЯ</u></b>\n\n"
                                     "Показаны последние 10 посещений.\n"
                                     "Нажмите на нужное посещение, чтобы получить заключение 📋\n\n"
                                     "Для того, чтобы показать еще 10 посещений, нажмите кнопку <b>Показать ещё</b>.",
                                     reply_markup=visit_list_menu)


@dp.callback_query_handler(visit_history_cb.filter())
async def send_visit_pdf(call: types.CallbackQuery, callback_data: dict):
    visit_pdf = mis_arianda.get_visit_pdf(callback_data['visit_id'], callback_data['visit_tp'])
    # повторная авторизация, если необходимо
    # http://80.73.198.109:7701/history/events/item/:tp/:id.pdf?tp=2149655268&id=visit
    pdf_url = visit_pdf.url
    # повспоминал как резать строки 😂😂 а потом вспомнил про callback_data...
    # pdf_url_splitted = pdf_url.split("?")
    # tp_id_splitted = pdf_url_splitted[1].split("&")
    # visit_tp = tp_id_splitted[0].lstrip("tp=")
    # visit_id = tp_id_splitted[1].lstrip("id=")
    visit_tp = callback_data['visit_tp']
    visit_id = callback_data['visit_id']
    visit_date = callback_data['visit_date']
    pdf_url_repl_tp = pdf_url.replace(":tp", visit_tp)
    pdf_url_repl_id = pdf_url_repl_tp.replace(":id", visit_id)
    pdf_url_replaced = pdf_url_repl_id.split("?")[0]
    print(pdf_url_replaced)
    to_menu_btn = types.InlineKeyboardMarkup(row_width=1)
    back_btn = types.InlineKeyboardButton("↩ Назад", callback_data='doctor_res')
    to_menu_btn.add(back_btn, main_menu_item)
    await call.message.delete()
    await bot.send_document(call.message.chat.id, types.InputFile.from_url(pdf_url_replaced),
                            caption=f"Заключение врача от {visit_date}")
    await call.message.answer('👆 Заключение врача находится в PDF-файле 📋', reply_markup=to_menu_btn)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
