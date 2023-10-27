from enum import Enum


class NotifType(Enum):
    ANSWERS = 'answer_notif'
    REVIEWS = 'review_notif'
    DEVELOP = 'develop_notif'


class Shop(Enum):
    KD = 'KD'
    OB = 'OB'
