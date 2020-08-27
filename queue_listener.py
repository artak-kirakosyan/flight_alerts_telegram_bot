try:
    from pprint import pprint
    import concurrent.futures
    from concurrent.futures import ThreadPoolExecutor
    import time
    import datetime

    from pymongo.errors import PyMongoError
    from pymongo.collection import Collection
    from telegram.utils.request import Request
    from telegram import Bot

    import config
    from helpers import get_collection, get_logger, Flight, APIClient, Alert

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
            file_name=config.QUEUE_LISTENER_LOG_PATH,
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
        self.airline_designator_collection = get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.AIRLINE_DESIGNATOR_DB,
            collection_name=config.AIRLINE_DESIGNATOR_COLLECTION,
        )
        self.thread_pool = ThreadPoolExecutor(max_workers=config.QUEUE_LISTENER_THREAD_POOL_SIZE)
        req = Request(
            connect_timeout=5,
        )

        self.bot = Bot(
            token=config.TG_TOKEN,
            request=req,
        )
        self.api_client = APIClient()

        self._logger.info("Listener created")

    def listen_to_queue(self):
        alerts = self.queue_collection.find({})
        try:
            num_alerts = alerts.count()
        except PyMongoError:
            self._logger.exception("Failed to get info from the DB.")
            raise RuntimeError("Failed to get info from the DB.")

        self._logger.info(f"Found {num_alerts} alerts in the queue, starting to process.")
        futures = [self.thread_pool.submit(self.process_alert, alert) for alert in alerts]
        self._futures = futures
        for future in concurrent.futures.as_completed(futures, timeout=10):
            if future.done():
                self._logger.info(f"Done with the current one: {future}.")

    def listen_forever(self):
        while True:
            self._logger.info("Starting to listen...")
            self.listen_to_queue()
            time.sleep(10)

    def insert_into(self, document: dict, collection: Collection):
        try:
            insertion_result = collection.insert_one(document)
        except PyMongoError:
            self._logger.exception("Failed to insert into collection.")
            raise RuntimeError("Failed to insert into collection.")
        else:
            return insertion_result

    def process_alert(self, alert_dict):
        """
        Process the alert from the queue, if valid, send to active, if too far, send to frozen alerts and remove
        from the queue:
        Arguments:
            :param alert_dict: dictionary containing chat_id, flight_data and date of the desired flight
        Returns:
            None
        """
        self._logger.info(f"Checking the alert {alert_dict['_id']}")
        if alert_dict['flight_data']['iata'] is None:
            airlines = self.airline_designator_collection.find(
                {
                    "icao": alert_dict['flight_data']['icao'],
                }
            )
            try:
                airlines = list(airlines)
            except PyMongoError:
                self._logger.exception(f"Failed to get info from the DB for alert {alert_dict}.")
                raise RuntimeError(f"Failed to get info from the DB for alert {alert_dict}.")
            if len(airlines) == 0:
                self._logger.warning(f"No corresponding airline IATA is found for alert {alert_dict}.")
                raise ValueError(f"No corresponding airline IATA is found for alert {alert_dict}.")
            if len(airlines) > 1:
                self._logger.warning(f'Multiple airlines detected for the alert {alert_dict}.')
                self._logger.warning("Taking the first one as a match.")
            else:
                self._logger.info(f"Found airline for alert {alert_dict}.")
            alert_dict['flight_data']['iata'] = airlines[0]['iata']

        alert_dict['flight_code'] = alert_dict['flight_data']['iata'] + alert_dict['flight_data']['flight_number']
        if alert_dict['date'] - datetime.timedelta(days=9) > datetime.datetime.today():
            self._logger.info("Flight date is too far from today, adding it to frozen")
            try:
                insertion_res = self.insert_into(alert_dict, self.frozen_collection)
                self.bot.send_message(
                    chat_id=alert_dict['chat_id'],
                    text="Your flight is too far from today, I will keep my eye on that ;)",
                )
            except RuntimeError:
                self._logger.exception("Failed to insert into frozen collection. Leaving it in ")
                raise RuntimeError(f"Failed to insert {alert_dict} into frozen.")

            if not insertion_res.acknowledged:
                self._logger.warning(f"Alert {alert_dict} was not inserted into frozen collection.")
                raise RuntimeError(f"Alert {alert_dict} was not inserted into the frozen: {insertion_res}")

            self._logger.info(f"Inserted {insertion_res.inserted_id} alert into frozen")
            self._logger.info(f"Removing {alert_dict} from the queue")
            try:
                self.queue_collection.delete_one({"_id": alert_dict['_id']})
            except PyMongoError:
                self._logger.exception(f"Failed to remove alert {alert_dict} from queue")
            else:
                self._logger.info(f"Removed alert {alert_dict} from the queue")
            return
        try:
            flight = self.api_client.get_flight_by_date(alert_dict['flight_code'], alert_dict['date'])
        except ValueError:
            self._logger.exception("Failed to get flight from the API.")
            self.bot.send_message(
                chat_id=alert_dict['chat_id'],
                text="Sorry I did not find any flight by your request, try again later",
            )
        else:
            if flight is None:
                self.bot.send_message(
                    chat_id=alert_dict['chat_id'],
                    text="Sorry I did not find any flight with your date.",
                )
            else:
                self._logger.info("Flight found, processing it.")
                alert = Alert(flight=flight, chat_id=alert_dict['chat_id'])
                self.bot.send_message(
                    chat_id=alert.chat_id,
                    text=str(alert.flight),
                )
                self._logger.info(f"Inserting {alert_dict['_id']} into active")
                self.insert_into(alert_dict, self.active_collection)
        self._logger.info(f"Removing {alert_dict['_id']} from queue")
        self.queue_collection.delete_one({"_id": alert_dict['_id']})
