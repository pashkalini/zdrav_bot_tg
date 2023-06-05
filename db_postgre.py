from datetime import datetime, timedelta

from sqlalchemy import create_engine, MetaData, Table, Boolean, String, Column, Integer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
import config

# engine = create_engine(f"postgresql+psycopg2://postgres:{config.DB_PASS}@localhost/postgres_db") # - для сервера
engine = create_engine("postgresql+psycopg2://postgres:MacPgDB@localhost/postgres")  # для локальной базы на маке
conn = engine.connect()

metadata = MetaData()

# таблица с токенами
tokens = Table('tokens', metadata,
               Column('chat_id', String(4096), primary_key=True, nullable=True),
               Column('save_auth', Boolean),
               Column('login_id', String(4096), nullable=True),
               Column('pass_id', String(4096), nullable=True),
               Column('token', String(4096), nullable=True)
               )

metadata.create_all(engine)


# Сохраняем токен
def save_token(tg_chat_id, api_token):
    insert_stmt = insert(tokens).values(
        chat_id=tg_chat_id,
        token=api_token
    )
    # замена значения токена в таблице на новую, при повторном вводе логина/пароля
    do_update_stmt = insert_stmt.on_conflict_do_update(
        constraint='tokens_pkey',
        set_=dict(token=api_token)
    )

    conn.execute(do_update_stmt)


# Записываем TRUE/FALSE статус для сохранения данных авторизации
def auth_save(tg_chat_id, tg_save_auth):
    insert_stmt_save = insert(tokens).values(
        chat_id=tg_chat_id,
        save_auth=tg_save_auth
    )

    update_stmt_save = insert_stmt_save.on_conflict_do_update(
        constraint='tokens_pkey',
        set_=dict(save_auth=tg_save_auth)
    )
    conn.execute(update_stmt_save)


# Сохраняем id логина авторизации
def save_login(tg_chat_id, tg_login_id):
    insert_stmt = insert(tokens).values(
        chat_id=tg_chat_id,
        login_id=tg_login_id
    )

    do_update_stmt = insert_stmt.on_conflict_do_update(
        constraint='tokens_pkey',
        set_=dict(login_id=tg_login_id)
    )
    conn.execute(do_update_stmt)


# Сохраняем id пароля авторизации
def save_pass(tg_chat_id, tg_pass_id):
    insert_stmt = insert(tokens).values(
        chat_id=tg_chat_id,
        pass_id=tg_pass_id
    )

    update_stmt = insert_stmt.on_conflict_do_update(
        constraint='tokens_pkey',
        set_=dict(pass_id=tg_pass_id)
    )
    conn.execute(update_stmt)


# Использование токена
def use_token(tg_chat_id):
    s = select([tokens.c.token]).where(tokens.c.chat_id == str(tg_chat_id))
    r = conn.execute(s)
    return r.fetchall()[0][0]


# Использование логина (id)
def use_login_id(tg_chat_id):
    s = select([tokens.c.login_id]).where(tokens.c.chat_id == str(tg_chat_id))
    r = conn.execute(s)
    return r.fetchall()[0][0]


# Использование пароля (id)
def use_pass_id(tg_chat_id):
    s = select([tokens.c.pass_id]).where(tokens.c.chat_id == str(tg_chat_id))
    r = conn.execute(s)
    return r.fetchall()[0][0]


# Использованием статуса хранения авторизации
def use_auth_save(tg_chat_id):
    s = select([tokens.c.save_auth]).where(tokens.c.chat_id == str(tg_chat_id))
    r = conn.execute(s)
    return r.fetchall()[0][0]


#  таблица для хранения дат для сервиса напоминаний о приеме
notifications = Table('notifications', metadata,
                      Column('id', Integer, primary_key=True),
                      Column('chat_id', String(4096), nullable=True),
                      Column('rnumb_id', String(4096), nullable=True),
                      Column('visit_date', String(4096), nullable=True),
                      Column('visit_info', String(4096), nullable=True)
                      )

metadata.create_all(engine)


#  сохранение даты визита к врачу
def save_visit_date(tg_chat_id, tg_rnumb_id, tg_visit_date, tg_visit_info):
    insert_stmt = insert(notifications).values(
        chat_id=tg_chat_id,
        rnumb_id=tg_rnumb_id,
        visit_date=tg_visit_date,
        visit_info=tg_visit_info
    )

    conn.execute(insert_stmt)


def check_visit_date():
    ntf_day = (datetime.today() + timedelta(days=11)).strftime('%d.%m.%Y')
    s = select([notifications.c.chat_id]).where(notifications.c.visit_date == ntf_day)
    r = conn.execute(s)
    return r.fetchall()


def delete_visit_date(tg_chat_id):
    delete_date = notifications.delete().where(notifications.c.chat_id == tg_chat_id)
    conn.execute(delete_date)


def use_visit_info(tg_chat_id):
    s = select([notifications.c.visit_info]).where(notifications.c.chat_id == str(tg_chat_id))
    r = conn.execute(s)
    res = r.fetchall()
    print(res)
    return res
