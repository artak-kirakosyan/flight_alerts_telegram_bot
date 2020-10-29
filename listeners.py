"""
Define listeners to process alerts.
"""
try:
    import concurrent.futures
    import datetime
    import multiprocessing
    import time

    import pymongo
    import pymongo.errors
    import telegram

    import common
    import config
    import helpers

except ImportError as exc:
    raise ImportError("Error occurred during import: %s" % (exc,))


class QueueListener(multiprocessing.Process):
    """
    Class that listens to the queued alerts and processes them.
    """
    def __init__(self):
        """
        This object is to listen to the queue in the DB,
        and if there is anything, process it.
        """
        super().__init__()
        self.alert_type = "queue"
        self._futures = None

        self._logger = common.get_logger(
            logger_name="QUEUE_LISTENER",
            file_name=config.QUEUE_LISTENER_LOG_PATH,
        )

        self.collection = common.get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.ALERT_DB,
            collection_name=config.ALERT_COLLECTION,
        )

        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.QUEUE_LISTENER_THREAD_POOL_SIZE)

        self.api_client = helpers.APIClient(
            logger_path=config.QUEUE_API_CLIENT_LOG_PATH,
            logger_name="QUEUE_API_CLIENT",
        )

        self.bot = telegram.Bot(
            token=config.TG_TOKEN,
        )

        self._logger.info("QueueListener created.")

    def get_all_relevant_alerts(self):
        """
        Query the DB to get current alerts.
        Returns:
            alerts: list of all relevant alerts
        """
        alerts = self.collection.find({"status": self.alert_type})
        try:
            num_alerts = alerts.count()
        except pymongo.errors.PyMongoError:
            self._logger.exception("Failed to get info from the DB.")
            raise RuntimeError("Failed to get info from the DB.")
        alerts = list(alerts)
        if len(alerts) == 0:
            self._logger.info("No queued alerts found")
        else:
            self._logger.info("Found %s queued alerts" % (num_alerts,))
        return alerts

    def listen_the_queue(self):
        """
        Get all alerts by type and process them.
        Returns:
            None
        """
        alerts = self.get_all_relevant_alerts()
        futures = [self.thread_pool.submit(self.process_alert, alert) for alert
                   in alerts]
        # for debugging purposes
        self._futures = futures
        for future in concurrent.futures.as_completed(futures, timeout=40):
            if future.done():
                self._logger.info("Exception: %s." % (future.exception()),)

    def run(self):
        """
        Function to execute when process.start() is called
        Returns:
            None
        """
        while True:
            self._logger.info("Checking queued...")
            self.listen_the_queue()
            time.sleep(30)

    def update_alert(self, alert_id, new_doc):
        """
        Update status of the alert
        Args:
            alert_id: _id of the alert
            new_doc: new status to be set
        Returns:
            None
        """
        self.collection.update_one(
            {"_id": alert_id},
            {
                "$set": new_doc
            }
        )

    def process_alert(self, alert_dict):
        """
        Process the alert, if too far, set to frozen, if valid, set to active,
        Args:
            alert_dict: dictionary with alert info.
        Returns:
            None
        """
        flight_code = alert_dict["flight_code"]
        flight_date = alert_dict['date']
        alert_id = alert_dict['_id']
        chat_id = alert_dict['chat_id']
        self._logger.info("Checking the alert %s" % (alert_id,))
        reply = None

        today = datetime.datetime.today()
        if flight_date - datetime.timedelta(days=9) > today:
            self._logger.info("Flight is too far, adding to frozen.")
            reply = "Flight %s is too far from today." % (flight_code,)
            reply += "I will keep my eye on it ;)"
            alert_dict['status'] = "frozen"
            self.update_alert(
                alert_id=alert_id,
                new_doc=alert_dict,
            )
            self._logger.info("Alert %s set to frozen" % (alert_id,))
        else:
            try:
                flight = self.api_client.get_flight_by_date(
                    flight_code=flight_code,
                    date=flight_date,
                )
            except ValueError:
                self._logger.exception("No results found at all")
                reply = "I count not find flight %s" % (flight_code,)
                reply += " on %s" % flight_date.strftime("%d/%m/%Y")
            else:
                if flight is None:
                    reply = "I count not find flight %s" % (flight_code,)
                    reply += " on %s" % flight_date.strftime("%d/%m/%Y")
                else:
                    self._logger.info("Found flight, setting to active.")
                    alert = helpers.Alert(
                        flight=flight,
                        chat_id=chat_id,
                        alert_id=alert_id,
                        status="active",
                    )
                    self.update_alert(
                        alert_id=alert_id,
                        new_doc=alert.to_dict(),
                    )
                    self._logger.info("Alert %s set to active" % (alert_id,))
        if reply is not None:
            self.bot.send_message(
                chat_id=chat_id,
                text=reply,
            )
        self._logger.info("Done with alert: %s" % (alert_id,))


class ActiveListener(multiprocessing.Process):
    """
    Class that listens to the active alerts and processes them.
    """
    def __init__(self):
        """
        This object is to listen to the active alerts in the DB,
        and if there is anything, process it.
        """
        super().__init__()
        self.alert_type = "active"
        self._futures = None

        self._logger = common.get_logger(
            logger_name="ACTIVE_LISTENER",
            file_name=config.ACTIVE_LISTENER_LOG_PATH,
        )

        self.collection = common.get_collection(
            connection_uri=config.MONGO_CONNECTION_URI,
            db_name=config.ALERT_DB,
            collection_name=config.ALERT_COLLECTION,
        )

        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.ACTIVE_LISTENER_THREAD_POOL_SIZE)

        self.api_client = helpers.APIClient(
            logger_path=config.ACTIVE_API_CLIENT_LOG_PATH,
            logger_name="ACTIVE_API_CLIENT",
        )

        self.bot = telegram.Bot(
            token=config.TG_TOKEN,
        )

        self._logger.info("ActiveListener created.")

    def get_all_relevant_alerts(self):
        """
        Query the DB to get current alerts.
        Returns:
            alerts: list of all relevant alerts
        """
        alerts = self.collection.find({"status": self.alert_type})
        try:
            num_alerts = alerts.count()
        except pymongo.errors.PyMongoError:
            self._logger.exception("Failed to get info from the DB.")
            raise RuntimeError("Failed to get info from the DB.")
        alerts = list(alerts)
        if len(alerts) == 0:
            self._logger.info("No active alerts found")
        else:
            self._logger.info("Found %s active alerts" % (num_alerts,))
        return alerts

    def listen_the_queue(self):
        """
        Get all alerts by type and process them.
        Returns:
            None
        """
        alerts = self.get_all_relevant_alerts()
        futures = [self.thread_pool.submit(self.process_alert, alert) for alert
                   in alerts]
        # for debugging purposes
        self._futures = futures
        for future in concurrent.futures.as_completed(futures, timeout=40):
            if future.done():
                self._logger.info("Exception: %s." % (future.exception()),)

    def run(self):
        """
        Function to execute when process.start() is called
        Returns:
            None
        """
        while True:
            self._logger.info("Checking active...")
            self.listen_the_queue()
            time.sleep(30)

    def update_alert(self, alert_id, new_doc):
        """
        Update status of the alert
        Args:
            alert_id: _id of the alert
            new_doc: new fields to be set
        Returns:
            None
        """
        self.collection.update_one(
            {"_id": alert_id},
            {
                "$set": new_doc
            }
        )

    def process_alert(self, alert_dict: dict):
        """
        Process the alert, if too far, set to frozen, if valid, set to active,
        Args:
            alert_dict: dictionary created by to_dict method of the Alert class.
        Returns:
            None
        """
        # @TODO implement logic here
        pass
