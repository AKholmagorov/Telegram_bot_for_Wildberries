import os
import sqlite3
import my_enums
import threading
from log_writer import logger

locker = threading.RLock()
db_name = 'sqlite_db.db'


def init():
    with locker:
        logger.info('init db...')

        is_db_existed = os.path.exists(db_name)
        logger.info(f'DB already existed: {is_db_existed}')

        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute("""
                CREATE TABLE IF NOT EXISTS chats(
                id INTEGER UNIQUE,
                answer_notif INTEGER,
                review_notif INTEGER,
                develop_notif INTEGER
                )
                """)

        c.execute("""
                CREATE TABLE IF NOT EXISTS late_review_chats(
                chat_id INTEGER UNIQUE,
                answer_notif INTEGER
                )
                """)

        c.execute("""
                CREATE TABLE IF NOT EXISTS unanswered_reviews(
                shop text,
                review_id text UNIQUE,
                ntf_already_snt INTEGER
                )
                """)

        c.execute("""
                CREATE TABLE IF NOT EXISTS past_review_ids(
                shop text,
                review_id text UNIQUE
                )
                """)

        # dates represent seconds (Unix TimeStamp)
        c.execute("""
                CREATE TABLE IF NOT EXISTS dates(
                name text UNIQUE,
                last_check_date INTEGER DEFAULT 0
                )
                """)

        # create last_check_date for shops if db didn't exist
        if not is_db_existed:
            c.execute("""INSERT INTO dates VALUES('KD_review_notif', 0)""")
            c.execute("""INSERT INTO dates VALUES('OB_review_notif', 0)""")
            c.execute("""INSERT INTO dates VALUES('broadcast_loop', 0)""")

        db.commit()
        db.close()

        logger.info('db was inited and closed')


def is_chat_exists(chat_id):
    logger.info('start: is_chat_exist()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"SELECT id FROM chats WHERE id = {chat_id}")
        existing_record = c.fetchone()
        db.close()

        if existing_record:
            logger.info('end: is_chat_exist() with True')
            return True
        else:
            logger.info('end: is_chat_exist() with False')
            return False


def add_chat(chat_id, answer_notif=0, review_notif=0, develop_notif=0):
    logger.info('start: add_chat()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                INSERT INTO chats VALUES({chat_id}, {answer_notif}, {review_notif}, {develop_notif})
                """)
        db.commit()
        db.close()

        logger.info(f'chat was added: {chat_id}')
        logger.info('end: add_chat()')


def remove_chat(chat_id):
    logger.info('start: remove_chat()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                DELETE FROM chats WHERE id = {chat_id}
                """)
        db.commit()
        db.close()

        logger.info(f'chat was deleted: {chat_id}')
        logger.info('end: remove_chat()')


# get chats id where special notification turn on
def get_chats(notif_type: my_enums.NotifType):
    logger.info('start: get_chats()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT id FROM chats WHERE {notif_type.value} = 1 
                """)

        chat_list = []

        for row in c.fetchall():
            chat_list.append(row[0])

        db.close()
        logger.info('end: get_chats()')
        return chat_list


def get_last_check_date(shop: my_enums.Shop, notif_type: my_enums.NotifType):
    logger.info('start: get_last_check_date()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT last_check_date FROM dates WHERE name = '{shop.value + '_' + notif_type.value}'
                """)

        last_check_date = c.fetchone()[0]

        db.close()
        logger.info('end: get_last_check_date()')
        return last_check_date


def update_last_check_date(shop: my_enums.Shop, notif_type: my_enums.NotifType, cur_time: int):
    logger.info('start: update_last_check_date()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                UPDATE dates SET last_check_date = {cur_time} WHERE name = '{shop.value + '_' + notif_type.value}'
                """)

        db.commit()
        db.close()
        logger.info('end update_last_check_date()')


def update_broadcast_last_check_date(cur_time: int):
    logger.info('start: update_broadcast_last_check_date()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                UPDATE dates SET last_check_date = {cur_time} WHERE name = 'broadcast_loop'
                """)

        db.commit()
        db.close()
        logger.info('end: update_broadcast_last_check_date()')


def get_broadcast_last_check_date():
    logger.info('start: get_broadcast_last_check_date()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT last_check_date FROM dates WHERE name = 'broadcast_loop'
                """)

        last_check_date = c.fetchone()[0]
        db.close()

        logger.info('end: get_broadcast_last_check_date()')
        return last_check_date


# invert chat notification value (0 will 1, 1 will 0)
def tune_chat(chat_id, notif_type: my_enums.NotifType):
    logger.info('start: tune_chat()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT {notif_type.value} FROM chats WHERE id = {chat_id}
                """)

        notif_value = c.fetchone()[0]  # get notif value (it's the first value in row)

        # возвращает значение, которое зависит от того включили или отключили уведомление
        if notif_value == 1:
            c.execute(f"""
                    UPDATE chats SET {notif_type.value} = 0 WHERE id = {chat_id}
                    """)

            db.commit()
            db.close()

            logger.info('end: tune_chat() with False')
            return False
        else:
            c.execute(f"""
                    UPDATE chats SET {notif_type.value} = 1 WHERE id = {chat_id}
                    """)

            db.commit()
            db.close()

            logger.info('end: tune_chat() with True')
            return True


def get_unanswered_ids(shop: my_enums.Shop):
    logger.info('start: get_unanswered_ids()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT review_id FROM unanswered_reviews WHERE shop = '{shop.value}'
                """)

        unanswered_ids = []
        for review_id in c.fetchall():
            unanswered_ids.append(review_id[0])

        db.close()
        logger.info('end: get_unanswered_ids()')
        return unanswered_ids


def get_unanswered_review_ntf_status(review_id):
    logger.info('start: get_unanswered_review_ntf_status()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT ntf_already_snt FROM unanswered_reviews WHERE review_id = '{review_id}'
                """)

        status = c.fetchall()
        db.close()
        logger.info('end: get_unanswered_review_ntf_status()')
        return status[0][0]


def make_unanswered_review_dirty(review_id):
    logger.info('start: make_unanswered_review_dirty()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                UPDATE unanswered_reviews SET ntf_already_snt = 1 WHERE review_id = '{review_id}'
                """)

        db.commit()
        db.close()
        logger.info('end: make_unanswered_review_dirty()')


def add_unanswered_review(review_id, shop: my_enums.Shop):
    logger.info('start: add_unanswered_review()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                INSERT INTO unanswered_reviews VALUES('{shop.value}', '{review_id}', 0)
                """)

        db.commit()
        db.close()
        logger.info('end: add_unanswered_review()')


def remove_unanswered_review(review_id):
    logger.info('start: remove_unanswered_review()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                DELETE FROM unanswered_reviews WHERE review_id = '{review_id}'
                """)

        db.commit()
        db.close()
        logger.info('end: remove_unanswered_review()')


def add_past_review_id(review_id, shop: my_enums.Shop):
    logger.info('start: add_past_review_id()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                INSERT INTO past_review_ids VALUES('{shop.value}', '{review_id}')
                """)

        db.commit()
        db.close()
        logger.info('end: add_past_review_id()')


def clear_past_review_ids(shop: my_enums.Shop):
    logger.info('start: clear_past_review_ids()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                DELETE FROM past_review_ids WHERE shop = '{shop.value}'
                """)

        db.commit()
        db.close()
        logger.info('end: clear_past_review_ids()')


def get_past_review_ids(shop: my_enums.Shop):
    logger.info('start: get_past_review_ids()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT review_id FROM past_review_ids WHERE shop = '{shop.value}'
                """)

        ids = []
        for review_id in c.fetchall():
            ids.append(review_id[0])

        db.close()
        logger.info('end: get_past_review_ids()')
        return ids


def add_late_review_chat(chat_id, answer_notif: 0):
    logger.info('[late_review_bot] start: add_late_review_chat()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                INSERT INTO late_review_chats VALUES({chat_id}, {answer_notif})
                """)
        db.commit()
        db.close()

        logger.info(f'[late_review_bot] chat was added: {chat_id}')
        logger.info('[late_review_bot] end: add_late_review_chat()')


def remove_late_review_chat(chat_id):
    logger.info('[late_review_bot] start: remove_late_review_chat()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                DELETE FROM late_review_chats WHERE chat_id = {chat_id}
                """)
        db.commit()
        db.close()

        logger.info(f'[late_review_bot] chat was deleted: {chat_id}')
        logger.info('[late_review_bot] end: remove_late_review_chat()')


def get_late_review_chats(notif_type: my_enums.NotifType):
    logger.info('[late_review_bot] start: get_late_review_chats()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"""
                SELECT chat_id FROM late_review_chats WHERE {notif_type.value} = 1 
                """)

        chat_list = []

        for row in c.fetchall():
            chat_list.append(row[0])

        db.close()
        logger.info('[late_review_bot] end: get_late_review_chats()')
        return chat_list


def is_late_review_chat_exists(chat_id):
    logger.info('[late_review_bot] start: is_late_review_chat_exists()')

    with locker:
        db = sqlite3.connect(db_name)
        c = db.cursor()

        c.execute(f"SELECT chat_id FROM late_review_chats WHERE chat_id = {chat_id}")
        existing_record = c.fetchone()
        db.close()

        if existing_record:
            logger.info('[late_review_bot] end: is_late_review_chat_exists() with True')
            return True
        else:
            logger.info('[late_review_bot] end: is_late_review_chat_exists() with False')
            return False
