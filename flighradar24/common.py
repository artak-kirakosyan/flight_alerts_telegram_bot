import logging


def get_logger(logger_name=__name__,
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
    file_handler = logging.FileHandler(file_name)
    file_handler.setFormatter(file_formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)

    logger = logging.getLogger(name=logger_name)
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
