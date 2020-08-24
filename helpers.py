try:
    import re
    import datetime
    import logging
    import requests

    from pymongo import collection, MongoClient
    from pymongo.errors import PyMongoError
    from telegram import Bot

    import config

except ImportError as e:
    raise ImportError(f'Error occurred during import: {e}\
    \nPlease install all necessary libraries and try again')


def get_logger(
        logger_name=__name__, 
        log_level=logging.DEBUG, 
        file_name='log.log', 
        file_format_str='%(asctime)s: %(levelname)s: %(name)s: %(message)s',
        stream_format_str='%(asctime)s: %(levelname)s: %(name)s: %(message)s'):
    """
    Create a logger and return.

    Arguments:
        logger_name: name of the logger, by default is __name__
        log_level: threshold level of the logging, by default is DEBUG
        file_name: name of the logging file, by default is log.log
        file_format_str: format of the logs for files
        stream_format_str: format of the logs for stream
    Return:
        logger: the created logger
    """
    file_formatter = logging.Formatter(file_format_str)
    stream_formatter = logging.Formatter(stream_format_str)

    file_handler = logging.FileHandler(file_name)
    file_handler.setFormatter(file_formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)

    logger = logging.getLogger(name=logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def get_collection(connection_uri: str, db_name: str, collection_name: str) -> collection:
    client = MongoClient(connection_uri)
    db = client.get_database(name=db_name)
    coll = db.get_collection(collection_name)
    return coll


def process_flight_code(flight_code: str) -> dict:
    """
        Take in the flight code and try to identify IATA, ICAO and flight num.

        Arguments:
            flight_code: string provided by the user
        Returns:
            data: dictionary of the parse data if any
        Raise ValueError if invalid input
    """
    flight_code = flight_code.upper()
    flight_code = re.match(config.FLIGHT_CODE_PATTERN, flight_code)
    if flight_code is None:
        raise ValueError("Invalid flight number")
    airline_code, flight_number = flight_code.groups()
    data = {'flight_number': flight_number}
    if len(airline_code) == 2:
        data['iata'] = airline_code
        data['icao'] = None
    else:
        data['iata'] = None
        data['icao'] = airline_code

    return data


def process_date(date_str: str) -> datetime.datetime:
    """
        Take in the string date and parse it
        Arguments:
            date_str: string given by the user
        Returns:
            date: datetime object
        Raise ValueError if invalid info provided.
        Raise
    """
    match = re.search(config.DATE_PATTERN, date_str)
    if match is None:
        raise ValueError("Invalid format for date.")
    day, month, year = match.groups()
    try:
        year = int(year)
        month = int(month)
        day = int(day)
        if year < 100:
            year += 2000
        date = datetime.datetime(year=year, month=month, day=day)
    except ValueError:
        raise ValueError("Invalid date")

    if datetime.datetime.today() - date > datetime.timedelta(days=2):
        raise ValueError("Date is too old")
    return date


def validate_queue_and_inform_user(user_data: dict, queue_collection: collection, bot: Bot):
    """
        This function takes in the data user supplied, validates it and saves to the mongodb
        Arguments:
            user_data: dictionary containing flight codes, date and chat_id
            queue_collection: pymongo collection object where to queue the alert
            bot: telegram.bot object which will inform the user about the queue writing results.
        Returns: None
    """
    try:
        response = queue_collection.insert_one(user_data)
    except PyMongoError as e:
        reply = "Something went wrong. Please try again later."
    else:
        if response.acknowledged:
            reply = "Alert is in queue. Will update shortly."
        else:
            reply = "Something went wrong. Please try again later."
    bot.send_message(
        chat_id=user_data['chat_id'],
        text=reply,
    )
