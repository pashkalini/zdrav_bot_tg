from sqlalchemy import create_engine, MetaData, Table, Integer, String, Column
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
import config

engine = create_engine(f"postgresql+psycopg2://postgres:{config.DB_PASS}@localhost/postgres_db")
conn = engine.connect()

metadata = MetaData()

tokens = Table('tokens', metadata,
               Column('id', Integer(), primary_key=True),
               Column('chat_id', String(4096), nullable=False),
               Column('token', String(4096), nullable=False),
               )

metadata.create_all(engine)


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


def use_token(tg_chat_id):
    s = select([tokens.c.token]).where(tokens.c.chat_id == str(tg_chat_id))
    r = conn.execute(s)
    return r.fetchall()[0][0]


