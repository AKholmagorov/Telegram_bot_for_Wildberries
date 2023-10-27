import wb
import time
import datetime
import my_enums
import review_bot
import late_review_bot
import threading
import my_db as db
from log_writer import logger

# Shop_1
OB_token = 'wildberries_token'
# Shop_2
KD_token = 'wildberries_token'

broadcast_delay = 60  # seconds


def broadcast_loop():
    while True:
        broadcast_is_run(True)
        logger.info('--- start broadcast_loop() ---')

        # check and send notification about new reviews
        review_bot.send_msgs(wb.get_new_reviews(OB_token, my_enums.Shop.OB), my_enums.NotifType.REVIEWS)
        review_bot.send_msgs(wb.get_new_reviews(KD_token, my_enums.Shop.KD), my_enums.NotifType.REVIEWS)

        # check and send notification about new answers
        review_bot.send_msgs(wb.get_new_answers(OB_token, my_enums.Shop.OB), my_enums.NotifType.ANSWERS)
        review_bot.send_msgs(wb.get_new_answers(KD_token, my_enums.Shop.KD), my_enums.NotifType.ANSWERS)

        # check and send notification about overdue answers
        late_review_bot.send_msgs(wb.get_overdue_reviews(OB_token, my_enums.Shop.OB), my_enums.NotifType.ANSWERS)
        late_review_bot.send_msgs(wb.get_overdue_reviews(KD_token, my_enums.Shop.KD), my_enums.NotifType.ANSWERS)

        cur_time = int(datetime.datetime.now().timestamp())
        db.update_broadcast_last_check_date(cur_time)
        broadcast_is_run(False)
        logger.info('--- end broadcast_loop() ---')

        time.sleep(broadcast_delay)


def broadcast_is_run(current_status: bool):
    try:
        with open('broadcast_status.txt', 'w') as file:
            file.write(str(current_status))
    except Exception as e:
        logger.warning(f'Error while write broadcast_status.txt: {e}')


if __name__ == '__main__':
    # open or create new db
    db.init()

    # Запуск потока для рассылки уведомлений
    broadcast_thread = threading.Thread(target=broadcast_loop)
    broadcast_thread.start()

    # Запуск потока для реакций на команды пользователя (review_bot)
    reaction_thread = threading.Thread(target=review_bot.bot_polling)
    reaction_thread.start()

    # Запуск потока для реакций на команды пользователя (late_review_bot)
    reaction_thread = threading.Thread(target=late_review_bot.bot_polling)
    reaction_thread.start()
