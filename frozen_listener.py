try:
    from pprint import pprint
    import concurrent.futures
    from concurrent.futures import ThreadPoolExecutor
    import time
    import datetime
    from multiprocessing import Process

    from pymongo.errors import PyMongoError
    from pymongo import UpdateOne
    from pymongo.collection import Collection
    from telegram.utils.request import Request
    from telegram import Bot

    import config
    from helpers import get_collection, get_logger, Flight, APIClient, Alert

except ImportError as exc:
    raise ImportError(f'Error occurred during import: {exc}\
    Please install all necessary libraries and try again')


class FrozenListener(Process):
    def __init__(self):
        """
        This object is to check the frozen queue in the DB, and if any update, process it.
        """
        super().__init__()
        self._futures = None
        self._logger = get_logger(
            logger_name="FROZEN_LISTENER",
            file_name=config.FROZEN_LISTENER_LOG_PATH,
        )
        self.queue_collection = get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.QUEUE_ALERT_DB,
            collection_name=config.QUEUE_COLLECTION,
        )
        self.frozen_collection = get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.FROZEN_ALERT_DB,
            collection_name=config.FROZEN_ALERT_COLLECTION,
        )
        self.active_collection = get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.ACTIVE_ALERTS_DB,
            collection_name=config.ACTIVE_ALERTS_COLLECTION,
        )
        self.thread_pool = ThreadPoolExecutor(max_workers=config.FROZEN_LISTENER_THREAD_POOL_SIZE)
        req = Request(
            connect_timeout=5,
        )
        self.bot = Bot(
            token=config.TG_TOKEN,
            request=req,
        )
        self.api_client = APIClient(
            logger_name="FROZEN_API_CLIENT",
            logger_path=config.FROZEN_API_CLIENT_LOG_PATH,
        )

        self._logger.info("FrozenListener created")

    def listen_to_queue(self):
        alerts = self.frozen_collection.find({})
        try:
            num_alerts = alerts.count()
        except PyMongoError:
            self._logger.exception("Failed to get info from the DB.")
            raise RuntimeError("Failed to get info from the DB.")

        self._logger.info(f"Found {num_alerts} alerts in the frozen queue, starting to process.")
        futures = [self.thread_pool.submit(self.process_alert, alert) for alert in alerts]
        # for debugging purposes
        self._futures = futures
        for future in concurrent.futures.as_completed(futures, timeout=40):
            if future.done():
                self._logger.info(f"Done with the current one: {future}.")

    def run(self):
        while True:
            self._logger.info("Starting to listen...")
            self.listen_to_queue()
            time.sleep(config.FROZEN_LISTENER_SLEEP_DURATION)

    def update_one(self, document: dict, collection: Collection):
        try:
            update_result = collection.update_one(
                {"_id": document["_id"]},
                {"$set": document},
                upsert=True,
            )
        except PyMongoError:
            self._logger.exception("Failed to insert into collection.")
            raise RuntimeError("Failed to insert into collection.")
        else:
            return update_result

    def process_alert(self, alert_dict):
        """
        Process the alert from the frozen queue, if valid, send to active and remove from frozen
        Arguments:
            :param alert_dict: dictionary containing chat_id, flight_data and date of the desired flight
        Returns:
            None
        """
        self._logger.info(f"Checking the alert {alert_dict['_id']}")
        reply = None
        if alert_dict['date'] - datetime.timedelta(days=9) > datetime.datetime.today():
            self._logger.info("Flight date is too far from today, leaving in frozen")

        # The case when the alert date is within accessible range
        else:
            try:
                flight = self.api_client.get_flight_by_date(alert_dict['flight_code'], alert_dict['date'])
            except ValueError:
                self._logger.exception("No results found at all")
                reply = f"I could not find flight {alert_dict['flight_code']}"
                reply += f" on {alert_dict['date'].strftime('%d/%m/%Y')}:/"
            else:
                if flight is None:
                    reply = f"Sorry I did not find {alert_dict['flight_code']}"
                    reply += f" on {alert_dict['date'].strftime('%d/%m/%Y')}."
                elif flight.properties["Real Arrival"] is not None:
                    self._logger.info("This flight has already arrived.")
                    reply = f"- - Your flight has already arrived - -\n"
                    reply += str(flight)
                elif flight.properties['Current Status'] == "Unknown":
                    self._logger.warning("Current status is missing.")
                    reply = f"Hmm, looks like I don't have info about your {flight.flight_code} flight."
                else:
                    self._logger.info("Flight found, processing it.")
                    alert = Alert(flight=flight, chat_id=alert_dict['chat_id'], alert_id=alert_dict["_id"])
                    reply = str(alert.flight)

                    self._logger.info(f"Inserting {alert_dict['_id']} into active")
                    self.update_one(alert.to_dict(), self.active_collection)
        if reply is not None:
            self.bot.send_message(
                chat_id=alert_dict['chat_id'],
                text=reply,
            )
            self._logger.info(f"Removing {alert_dict['_id']} from frozen queue")
            self.frozen_collection.delete_one({"_id": alert_dict['_id']})
