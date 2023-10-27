import os
import time
import datetime
import subprocess
from log_writer import logger


# Данный модуль запускается через cron раз в сутки, чтобы удалить старые логи и перезагрузить систему.
# Также происходит проверка, что рассылка в данный момент не активна, чтобы не прервать ее работу.


def remove_old_logs():
    logs_directory = 'logs'

    days_threshold = 14
    current_date = datetime.datetime.now()

    for filename in os.listdir(logs_directory):
        if filename.endswith('.log'):
            file_path = os.path.join(logs_directory, filename)

            modified_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            days_difference = (current_date - modified_date).days

            if days_difference > days_threshold:
                os.remove(file_path)
                logger.info(f"[reboot]: Log file was deleted: {filename}")


def is_broadcast_active() -> bool:
    while True:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            broadcast_status_file = os.path.join(script_dir, 'broadcast_status.txt')
            with open(broadcast_status_file, 'r') as file:
                value = file.readline() == 'True'
                logger.info(f"[reboot]: broadcast is active: {value}")
                return value
        except Exception as e:
            logger.error(f'[reboot]: Error while read broadcast_status.txt: {e}. Try again in 10 seconds...')
            time.sleep(10)


def reboot_system():
    while True:
        if not is_broadcast_active():
            logger.info('[reboot]: System is launching reboot...')
            subprocess.run(["reboot"])
            break
        else:
            logger.info('[reboot]: System is waiting for reboot. Next attempt in 10 seconds...')
            time.sleep(10)


if __name__ == '__main__':
    remove_old_logs()
    reboot_system()
