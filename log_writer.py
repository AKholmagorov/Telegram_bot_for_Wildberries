import logging
import datetime
import os

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[
        logging.FileHandler('logs/log_{:%Y-%m-%d}.log'.format(datetime.datetime.now())),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger()
