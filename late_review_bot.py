import time
import telebot
import my_enums
import my_db as db
from log_writer import logger

bot = telebot.TeleBot('your_tg_bot_token')


# send messages to users
def send_msgs(msg_list, notif_type: my_enums.NotifType):
    logger.info(f'[late_review_bot] start: send_msgs(), notif_type: {notif_type.value}')
    chat_list = db.get_late_review_chats(notif_type)

    for chat in chat_list:
        for msg in msg_list:
            try:
                bot.send_message(chat, msg, parse_mode='html')
                logger.info(f'[late_review_bot] msg sent to chat: {chat}')
            except Exception as e:
                if isinstance(e, telebot.apihelper.ApiTelegramException) and e.result_json['error_code'] == 403:
                    logger.info(f"[late_review_bot] chat {chat}: user blocked bot (Error: {e.result_json['error_code']})")
                    db.remove_late_review_chat(chat)
                    break
                else:
                    logger.warning(f"[late_review_bot] Couldn't send msg to chat: {chat}. Error: {e}")

            time.sleep(0.5)  # delay before send next message

    logger.info(f'[late_review_bot] end: send_msgs(), notif_type: {notif_type.value}')


def bot_polling():
    while True:
        try:
            logger.info('[late_review_bot] thread_3: start bot.polling(none_stop=True)')
            bot.polling(none_stop=True)
        except Exception as e:
            logger.warning(f'[late_review_bot] thread_3: an error occurred during bot.polling(none_stop=True): {e}' + \
                           f'\nRestart in 10 seconds...')
            time.sleep(10)


@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f'[late_review_bot] chat {message.chat.id} called "/start"')


@bot.message_handler(func=lambda message: message.text.lower() == 'ответы')
def answers(message):
    logger.info(f'[late_review_bot] chat {message.chat.id} called "ответы"')

    if not db.is_late_review_chat_exists(message.chat.id):
        db.add_late_review_chat(message.chat.id, 1)
        bot.send_message(message.chat.id, 'Вы подписались на уведомления об ответах с 10-ти минутной задержкой!')


# реакция на любое сообщение, кроме выше стоящих
# должно находиться под остальными командами/кодовыми словами
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    logger.info(f'[late_review_bot] chat {message.chat.id} messaged: {message.text}')
