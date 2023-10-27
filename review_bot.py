import time
import telebot
import my_enums
import my_db as db
from log_writer import logger

bot = telebot.TeleBot('your_tg_bot_token')


# send messages to users
def send_msgs(msg_list, notif_type: my_enums.NotifType):
    logger.info(f'start: send_msgs(), notif_type: {notif_type.value}')
    chat_list = db.get_chats(notif_type)

    for chat in chat_list:
        for msg in msg_list:
            try:
                bot.send_message(chat, msg, parse_mode='html')
                logger.info(f'msg sent to chat: {chat}')
            except Exception as e:
                if isinstance(e, telebot.apihelper.ApiTelegramException) and e.result_json['error_code'] == 403:
                    logger.info(f"chat {chat}: user blocked bot (Error: {e.result_json['error_code']})")
                    db.remove_chat(chat)
                    break
                else:
                    logger.warning(f"Couldn't send msg to chat: {chat}. Error: {e}")

            time.sleep(0.5)  # delay before send next message

    logger.info(f'end: send_msgs(), notif_type: {notif_type.value}')


def bot_polling():
    while True:
        try:
            logger.info('thread_2: start bot.polling(none_stop=True)')
            bot.polling(none_stop=True)
        except Exception as e:
            logger.warning(f'thread_2: an error occurred during bot.polling(none_stop=True): {e}' + \
                           f'\nRestart in 10 seconds...')
            time.sleep(10)


@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f'chat {message.chat.id} called "/start"')


# reaction for code phrases
@bot.message_handler(func=lambda message: message.text.lower() == 'отзывы')
def reviews(message):
    logger.info(f'chat {message.chat.id} called "отзывы"')

    if db.is_chat_exists(message.chat.id):
        if db.tune_chat(message.chat.id, my_enums.NotifType.REVIEWS):
            bot.send_message(message.chat.id, 'Уведомления для отзывов включены')
        else:
            bot.send_message(message.chat.id, 'Уведомления для отзывов отключены')
    else:
        db.add_chat(message.chat.id, 0, 1, 0)
        bot.send_message(message.chat.id, 'Вы подписались на уведомления о новых отзывах!')


@bot.message_handler(func=lambda message: message.text.lower() == 'ответы')
def answers(message):
    logger.info(f'chat {message.chat.id} called "ответы"')

    if db.is_chat_exists(message.chat.id):
        if db.tune_chat(message.chat.id, my_enums.NotifType.ANSWERS):
            bot.send_message(message.chat.id, 'Уведомления для ответов включены')
        else:
            bot.send_message(message.chat.id, 'Уведомления для ответов отключены')
    else:
        db.add_chat(message.chat.id, 1, 0, 0)
        bot.send_message(message.chat.id, 'Вы подписались на уведомления о новых ответах!')


# reaction for code phrases
@bot.message_handler(func=lambda message: message.text.lower() == 'work?')
def develop(message):
    bot.send_message(message.chat.id, 'yes')


# реакция на любое сообщение, кроме выше стоящих
# должно находиться под остальными командами/кодовыми словами
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    logger.info(f'chat {message.chat.id} messaged: {message.text}')
