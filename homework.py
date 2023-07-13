import logging
import os
import time
import sys

import requests
import telegram

from dotenv import load_dotenv
from exceptions import ApiError, EmptyTokenError, MainBodyError, ParseError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Check tokens existense.

    :raises EmptyTokenError: if at least one of the tokens is empty.
        Custom error, children of Exception class.
    """
    if not (PRACTICUM_TOKEN or TELEGRAM_TOKEN or TELEGRAM_CHAT_ID):
        logging.critical('check_tokens func doesnt work')
        raise EmptyTokenError('tokens should not be empty!')


def send_message(bot, message: str) -> None:
    """Send message into <TELEGRAM_CHAT_ID> chat.

    :param bot: this is class example of telegram.Bot() class.
    :param message: this is the text string (str) we would like to send.
    :raises SendMessageError: if message cannot be sent.
        Custom error, children of Exception class.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'send_message works, {message}')

    except Exception as error:
        logging.error(f'{error}, send_message')


def get_api_answer(timestamp: int) -> dict:
    """Send request to the <ENDPOINT> adress.

    :param timestamp: this is digit (int) represent time in ms (Unix time).
    :returns: API answer (json) converted to python dict class.
    :raises ApiError: if <ENDPOINT> does not respond.
        Custom error, children of Exception class.
    """
    payload = {'from_date': timestamp - RETRY_PERIOD}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            raise ApiError(f'cannot connect to {ENDPOINT}')
        return response.json()

    except Exception as error:
        logging.error(f'{error}, get_api_answer')
        raise ApiError(f'cannot connect to {ENDPOINT}')


def check_response(response: dict) -> None:
    """Send request to the <ENDPOINT> adress.

    :param response: type dict, represent information we were given via API.
    :raises TypeError: if <response> does not match YAPracticum documentation
    """
    if type(response) is not dict:
        raise TypeError('response is not a dict type')
    elif type(response.get('homeworks')) is not list:
        raise TypeError('value of homeworks is not list')


def parse_status(homework: dict) -> str:
    """Acquire status from <homework> (dict).

    :param homework:
    :returns: text string (str) with homework status
    :raises ParseError: if <homework> does not have any of legit statuses
        or homewor_name key not in <homework>.
        Custom error, children of Exception class.
    """
    if 'status' not in homework:
        raise ParseError('status not in homework!')
    elif homework['status'] not in HOMEWORK_VERDICTS:
        raise ParseError('status does not match legit status names')

    if not homework.get('homework_name'):
        raise ParseError('homework_name not in homework')

    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Main bot logic.
    Call api with <get_api_answer> func.
    Check if respons is allright with <check_response> func.
    Get homework status throught <parse_status> func.
    Send message with <send_message> func.
    Repeat proccess every <RETRY_PERIOD> time.

    :raises MainBodyError: if anything goes wrong.
        Custom error, children of Exception class.
    """
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:

        try:
            response = get_api_answer(timestamp=timestamp)
            check_response(response=response)
            if (homework := response['homeworks']):
                homework = homework[0]
                status = parse_status(homework=homework)
                send_message(bot=bot, message=status)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.debug(message)
            raise MainBodyError(f'{message}')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
