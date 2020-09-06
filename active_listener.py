try:
    import concurrent.futures
    import time
    import datetime
    import multiprocessing

    import pymongo
    import pymongo.errors
    import telegram

    import config
    import common
    import helpers
except ImportError as exc:
    raise ImportError(f'Error occurred during import: {exc}\
    Please install all necessary libraries and try again')


class ActiveListener(multiprocessing.Process):
    def __init__(self):
        """
        This object is to check the ACTIVE alerts in the DB, and if any update, process it.
        """
        super().__init__()
        self._futures = None
        self._logger = common.get_logger(
            logger_name="ACTIVE_LISTENER",
            file_name=config.ACTIVE_LISTENER_LOG_PATH,
        )
        self.active_collection = common.get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.ACTIVE_ALERTS_DB,
            collection_name=config.ACTIVE_ALERTS_COLLECTION,
        )
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=config.ACTIVE_LISTENER_THREAD_POOL_SIZE)
        self.bot = telegram.Bot(
            token=config.TG_TOKEN,
        )
        self.api_client = helpers.APIClient(
            logger_name="ACTIVE_API_CLIENT",
            logger_path=config.ACTIVE_API_CLIENT_LOG_PATH,
        )

        self._logger.info("ActiveListener created")

    def listen_to_queue(self):
        alerts = self.active_collection.find({})
        try:
            num_alerts = alerts.count()
        except pymongo.errors.PyMongoError:
            self._logger.exception("Failed to get info from the DB.")
            raise RuntimeError("Failed to get info from the DB.")

        self._logger.info(f"Found {num_alerts} alerts in the active alerts, starting to process.")
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
            time.sleep(config.ACTIVE_LISTENER_SLEEP_DURATION)

    def update_one(self, document: dict, collection: pymongo.collection.Collection):
        try:
            update_result = collection.update_one(
                {"_id": document["_id"]},
                {"$set": document},
                upsert=True,
            )
        except pymongo.errors.PyMongoError:
            self._logger.exception("Failed to insert into collection.")
            raise RuntimeError("Failed to insert into collection.")
        else:
            return update_result

    def process_alert(self, alert_dict):
        """
        Process the alert from the active alerts. If already landed, remove from active.
        If status changes in the flight, report to the user.
        Arguments:
            :param alert_dict: dictionary containing chat_id, flight_data and date of the desired flight
        Returns:
            None
        """
        self._logger.info(f"Checking the alert {alert_dict['_id']}")
        current_alert = helpers.Alert.from_dict(alert_dict=alert_dict)
        to_delete = False
        try:
            flight = self.api_client.get_flight_by_id(
                flight_code=alert_dict['flight']['flight_code'],
                flight_id=alert_dict['flight']['flight_id'],
            )
        except ValueError:
            self._logger.exception("No results found at all")
            reply = f"I could not find flight {alert_dict['flight']['flight_code']}"
        else:
            if flight is None:
                reply = f"Sorry I did not find {alert_dict['flight']['flight_code']}"
                to_delete = True
            elif flight.properties["Real Arrival"] is not None:
                self._logger.info("This flight has already arrived.")
                reply = f"- - Your flight has already arrived - -\n"
                reply += str(flight)
                to_delete = True
            elif flight.properties['Current Status'] == "Unknown":
                self._logger.warning("Current status is missing.")
                reply = f"Hmm, looks like I don't have info about your {flight.flight_code} flight."
                to_delete = True
            else:
                self._logger.info("Flight found, processing it.")
                new_alert = helpers.Alert(flight=flight, chat_id=alert_dict['chat_id'], alert_id=alert_dict["_id"])
                reply = current_alert.create_status_update(new_alert)
                if reply is not None:
                    self.update_one(new_alert.to_dict(), self.active_collection)

        if reply is not None:
            self.bot.send_message(
                chat_id=alert_dict['chat_id'],
                text=reply,
            )
        if to_delete:
            self._logger.info(f"Removing {alert_dict['_id']} from active queue")
            self.active_collection.delete_one({"_id": alert_dict['_id']})
