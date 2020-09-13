"""
This module contains functions that are used by different modules.
"""
try:
    import logging

    import pymongo

except ImportError as exc:
    raise ImportError("Error occurred during import: %s" % (exc,))


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
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def get_collection(
        connection_uri: str,
        db_name: str,
        collection_name: str) -> pymongo.collection.Collection:
    """
    Create and return pymongo Collection object.
    Arguments:
        connection_uri: MongoDB connection URI
        db_name: the name of the DB to connect
        collection_name: the name of the collection in the db to get.
    """
    client = pymongo.MongoClient(connection_uri)
    db = client.get_database(name=db_name)
    coll = db.get_collection(collection_name)
    return coll
