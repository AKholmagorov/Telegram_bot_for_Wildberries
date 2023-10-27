import re
import time
import requests
import my_enums
import datetime
import my_db as db
from log_writer import logger


def get_new_reviews(wb_api_token, shop: my_enums.Shop):
    logger.info(f'start: get_new_reviews() for {shop.value}')

    new_feedbacks = []
    last_check_date = db.get_last_check_date(shop, my_enums.NotifType.REVIEWS)

    url = 'https://feedbacks-api.wb.ru/api/v1/feedbacks'
    headers = {
        'Authorization': f'{wb_api_token}'
    }
    params = {
        'isAnswered': 'false',
        'take': '5000',
        'skip': '0',
        'dateFrom': f'{last_check_date}'
    }

    cur_time = int(datetime.datetime.now().timestamp())
    response = get_response_with_retry(url, headers, params, shop)
    if response is None:
        logger.warning(f'end: get_new_reviews() with None for {shop.value}')
        return new_feedbacks

    if response.status_code == 200 and len(response.json()['data']['feedbacks']) > 0:
        db.update_last_check_date(shop, my_enums.NotifType.REVIEWS, cur_time)

        # add new unanswered feedbacks to the list
        feedbacks = response.json()['data']['feedbacks']
        past_feedbacks_ids = db.get_past_review_ids(shop)

        # form messages from new unanswered reviews
        for feedback in feedbacks:
            # sometimes feedback can be duplicated, this 'if' will prevent it
            if feedback['id'] in past_feedbacks_ids:
                logger.warning(f"duplicated feedback was deleted. ID: {feedback['id']}")
                continue

            feedback_text = feedback['text'] if feedback['text'] != '' else 'отсутствует'
            new_feedbacks.append('<b><u>Добавлен новый отзыв!</u></b>' + \
                                 '\n\n<b>Магазин:</b> ' + feedback['productDetails']['brandName'] + \
                                 '\n\n<b>Оценка:</b> ' + str(feedback['productValuation']) + \
                                 '\n<b>Комментарий:</b><i> ' + feedback_text + '</i>' + \
                                 '\n\n<b>Отзыв оставлен: </b>' + remove_sz_from_date(feedback['createdDate']) + \
                                 '\n<b>ID:</b> ' + feedback['id'])

        # update past reviews list
        db.clear_past_review_ids(shop)
        for feedback in feedbacks:
            db.add_past_review_id(feedback['id'], shop)

    elif response.status_code == 200:
        db.update_last_check_date(shop, my_enums.NotifType.REVIEWS, cur_time)
    else:
        logger.warning(f'get_new_reviews(): Shop: {shop}. Response code: {response.status_code} ' + str(response.text))
        logger.warning('get_new_reviews(): response code not 2xx so try later')

    logger.info(f'end: get_new_reviews() for {shop.value}')
    return new_feedbacks


def get_new_answers(wb_api_token, shop: my_enums.Shop):
    logger.info(f'start: get_new_answers() for {shop.value}')

    new_answers = []
    # don't show answer creation date if error is more than this
    max_error_delay = 120  # seconds

    url = 'https://feedbacks-api.wb.ru/api/v1/feedbacks'
    headers = {
        'Authorization': f'{wb_api_token}'
    }
    params = {
        'isAnswered': 'false',
        'take': '5000',
        'skip': '0',
    }

    response = get_response_with_retry(url, headers, params, shop)
    if response is None:
        logger.warning(f'end: get_new_answers() with None for {shop.value}')
        return new_answers
    elif len(response.json()['data']['feedbacks']) > 100:
        logger.warning(f"Too much unprocessed reviews: {len(response.json()['data']['feedbacks'])}. Program may work "
                       f"slowly")

    if response.status_code == 200:
        feedbacks = response.json()['data']['feedbacks']
        old_feedback_ids = db.get_unanswered_ids(shop)
        current_feedback_ids = []

        # get current unanswered review ids
        for feedback in feedbacks:
            current_feedback_ids.append(feedback['id'])

        # find old review in current_review_list. If it's not in, delete that from db and send
        for old_feedback_id in old_feedback_ids:
            if old_feedback_id not in current_feedback_ids:
                feedback = get_review_by_id(old_feedback_id, wb_api_token, shop)

                if feedback is None:
                    logger.warning('feedback is None')
                    continue
                elif feedback['answer'] is None:
                    db.remove_unanswered_review(old_feedback_id)
                    logger.info('review was deleted from DB because it was deleted in wb')
                    continue

                cur_time = int(datetime.datetime.now().timestamp())

                # не указывать дату написания ответа, если погрешность более X секунд
                if db.get_broadcast_last_check_date() + max_error_delay > cur_time:
                    answer_received = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                else:
                    answer_received = '<i>не удалось установить</i>'

                feedback_text = '\n<i>' + feedback['text'] + '</i>' if feedback['text'] != '' else '<i>отсутствует</i>'
                feedback_answer = '\n<i>' + feedback['answer']['text'] + '</i>' if feedback['answer']['text'] != '' else '<i>отсутствует</i>'

                new_answers.append(f'<b><u>Добавлен новый ответ!</u></b>' + \
                                   '\n\n<b>Магазин:</b> ' + feedback['productDetails']['brandName'] + \
                                   '\n\n<b>Оценка:</b> ' + str(feedback['productValuation']) + \
                                   '\n<b>Комментарий:</b> ' + feedback_text + \
                                   '\n\n<b>Ответ продавца:</b> ' + feedback_answer + \
                                   '\n\n<b>Отзыв оставлен:</b> ' + remove_sz_from_date(feedback['createdDate']) + \
                                   f'\n<b>Ответ получен:</b> {answer_received}' + \
                                   f"\n\n<b>Артикул:</b> {feedback['productDetails']['nmId']}" + \
                                   '\n<b>ID:</b> ' + feedback['id'])

                db.remove_unanswered_review(old_feedback_id)

        # add current unanswered review if it's not in db
        for current_feedback_id in current_feedback_ids:
            if current_feedback_id not in old_feedback_ids:
                db.add_unanswered_review(current_feedback_id, shop)
    else:
        logger.warning(f'Shop: {shop}. Response code: ' + str(response.status_code) + str(response.text))

    logger.info(f'end: get_new_answers() for {shop.value}')
    return new_answers


def get_overdue_reviews(wb_api_token, shop: my_enums.Shop):
    logger.info(f'start: get_overdue_reviews() for {shop.value}')

    overdue_answers = []
    overdue_limit = 600  # seconds

    url = 'https://feedbacks-api.wb.ru/api/v1/feedbacks'
    headers = {
        'Authorization': f'{wb_api_token}'
    }
    params = {
        'isAnswered': 'false',
        'take': '5000',
        'skip': '0',
    }

    response = get_response_with_retry(url, headers, params, shop)
    if response is None:
        logger.warning(f'end: get_overdue_reviews() with None for {shop.value}')
        return overdue_answers

    feedbacks = response.json()['data']['feedbacks']
    current_unanswered_reviews = db.get_unanswered_ids(shop)
    cur_time = int(datetime.datetime.now().timestamp())

    for feedback in feedbacks:
        is_overdue = convert_sz_date_to_timestamp(feedback['createdDate']) < cur_time - overdue_limit
        # is_work_time = is_time_between_9_and_21(feedback['createdDate'])

        # заказчик решил отправлять уведомления о задержке в нерабочее время.
        # с большей вероятностью он передумает. тогда условие нужно заменить на нижестоящее
        # if is_overdue and is_work_time and feedback['id'] in current_unanswered_reviews:

        if is_overdue and feedback['id'] in current_unanswered_reviews:
            review_ntf_status = db.get_unanswered_review_ntf_status(feedback['id'])
            # check if ntf about this review wasn't sent yet
            if review_ntf_status == 0:
                feedback_text = '\n<i>' + feedback['text'] + '</i>' if feedback['text'] != '' else '<i>отсутствует</i>'
                overdue_answers.append(f'<b><u>На отзыв нет ответа более 10 минут</u></b>' + \
                                       '\n\n<b>Магазин:</b> ' + feedback['productDetails']['brandName'] + \
                                       '\n\n<b>Оценка:</b> ' + str(feedback['productValuation']) + \
                                       '\n<b>Комментарий:</b> ' + feedback_text + \
                                       '\n\n<b>Отзыв оставлен:</b> ' + remove_sz_from_date(feedback['createdDate']) + \
                                       f"\n\n<b>Артикул:</b> {feedback['productDetails']['nmId']}" + \
                                       '\n<b>ID:</b> ' + feedback['id'])
                db.make_unanswered_review_dirty(feedback['id'])

    logger.info(f'end: get_overdue_reviews() for {shop.value}')
    return overdue_answers


def get_review_by_id(review_id, wb_api_token, shop: my_enums.Shop):
    logger.info(f'start: get_review_by_id() for {shop.value}')

    url = 'https://feedbacks-api.wb.ru/api/v1/feedback'
    headers = {
        'Authorization': f'{wb_api_token}'
    }
    params = {
        'id': f'{review_id}'
    }

    response = get_response_with_retry(url, headers, params, shop)
    if response is None:
        logger.warning(f'end: get_review_by_id() with None for {shop.value}')
        return None
    else:
        logger.info(f'end: get_review_by_id() for {shop.value}')
        return response.json()['data']


def get_response_with_retry(url, headers, params, shop: my_enums.Shop, max_retries=3, retry_delay=10):
    logger.info(f'start: get_response_with_retry() for {shop.value}')

    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()  # Raises an exception for non-2xx responses
            logger.info(f'end: get_response_with_retry() for {shop.value}')
            return response
        except Exception as e:
            if isinstance(e, requests.exceptions.RequestException):
                if max_retries > 0:
                    max_retries -= 1
                    logger.warning(f'Shop {shop.value}. An error occurred: {e}. Retrying in {retry_delay} seconds...')
                    time.sleep(retry_delay)
                else:
                    logger.warning('Max retries reached. Could not establish connection.')

                    if e.response is None:
                        print('e.response is None')
                        return None

                    if e.response.status_code == 422:
                        pattern = r'id=(\d+)'
                        match = re.search(pattern, str(e))
                        if match:
                            review_id = match.group(1)
                            db.remove_unanswered_review(review_id)
                            logger.warning(f'ID ({review_id}) was deleted from db because it does not exist anymore')

                    logger.info(f'end: get_response_with_retry() for {shop.value}')
                    return None
            else:
                logger.error(f'Unknown exception in get_response_with_retry(): {e}')
                logger.info(f'end: get_response_with_retry() for {shop.value}')
                return None


def remove_sz_from_date(date):
    logger.info(f'start: convert_date()')

    # Преобразование полученной даты в объект datetime
    input_datetime = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')

    # Перевод времени на МСК
    adjusted_datetime = input_datetime + datetime.timedelta(hours=3)

    # Форматирование даты и времени в требуемом формате
    logger.info(f'end: convert_date()')
    return adjusted_datetime.strftime('%Y-%m-%d %H:%M')


def convert_sz_date_to_timestamp(sz_date_string):
    logger.info(f'start: convert_sz_date_to_timestamp()')

    # Преобразование строки в объект datetime
    date_object = datetime.datetime.strptime(sz_date_string, "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(hours=3)
    timestamp = date_object.timestamp()

    logger.info(f'end: convert_sz_date_to_timestamp()')
    return timestamp


def is_time_between_9_and_21(date_string):
    logger.info(f'start: is_time_between_9_and_21()')

    date_obj = datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    date_obj += datetime.timedelta(hours=3)  # Установка времени МСК

    start_time = datetime.datetime(date_obj.year, date_obj.month, date_obj.day, 9, 0, 0)
    end_time = datetime.datetime(date_obj.year, date_obj.month, date_obj.day, 21, 0, 0)

    if start_time <= date_obj <= end_time:
        logger.info(f'end: is_time_between_9_and_21()')
        return True
    else:
        logger.info(f'end: is_time_between_9_and_21()')
        return False
