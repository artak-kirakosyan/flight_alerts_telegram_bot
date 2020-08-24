try:
    from pprint import pprint
    import concurrent.futures
    from concurrent.futures import ThreadPoolExecutor
    import time

    from pymongo.errors import PyMongoError
    from telegram.utils.request import Request
    from telegram import Bot

    import config
    from helpers import get_collection, get_logger

except ImportError as e:
    raise ImportError(f'Error occurred during import: {e}\
    Please install all necessary libraries and try again')


class Listener:
    def __init__(self):
        """
        This object is to listen to the queue in the DB, and if there is anything, process it.
        """
        self._logger = get_logger(
            logger_name="QUEUE_LISTENER",
            file_name="listen_queue.log",
        )
        self.collection = get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.QUEUE_ALERT_DB,
            collection_name=config.QUEUE_COLLECTION,
        )
        self.thread_pool = ThreadPoolExecutor(2)
        req = Request(
            connect_timeout=5,
        )

        self.bot = Bot(
            token=config.TG_TOKEN,
            request=req,
        )
        self._logger.info("Listener created")

    def listen_to_queue(self):
        alerts = self.collection.find({})
        try:
            num_alerts = alerts.count()
        except PyMongoError as e:
            self._logger.exception("Failed to get info from the DB.")
            raise RuntimeError("Failed to get info from the DB.")

        self._logger.info(f"Found {num_alerts} alerts in the queue, starting to process.")
        # self._logger.info(f"Submitting alert: {alert}")
        # for alert in alerts:
        futures = [self.thread_pool.submit(self.check_alert, alert) for alert in alerts]
        for future in concurrent.futures.as_completed(futures, timeout=10):
            print(future.result())

    def check_alert(self, alert_dict):
        self._logger.info("Checking the alert:")
