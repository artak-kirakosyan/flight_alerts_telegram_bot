"""
Configs of the telegram bot and its
"""
try:
    import os
except ImportError as exc:
    raise ImportError("Error occurred during import: %s" % (exc,))

# Telegram bot and parse configs
TG_TOKEN = os.getenv("TG_TOKEN")
BOT_LOG_PATH = "logs/bot.log"

FLIGHT_CODE_PATTERN_PLAIN = r"([A-Z0-9]{2}|[A-Z]{3})\s*([0-9]{1,4})"
DATE_PATTERN_PLAIN = r"(\d{1,2})[-.,/;:_](\d{1,2})[-.,/;:_](\d{2,4})"
TIME_PATTERN_PLAIN = r"(\d{2})[-.,/;:_](\d{2})"
DATETIME_PATTERN_PLAIN = DATE_PATTERN_PLAIN + r"\s*" + TIME_PATTERN_PLAIN
FULL_PATTERN_PLAIN = FLIGHT_CODE_PATTERN_PLAIN + r"\s*" + DATETIME_PATTERN_PLAIN

FLIGHT_CODE_PATTERN = r"^\s*" + FLIGHT_CODE_PATTERN_PLAIN + r"\s*$"
DATE_PATTERN = r"^\s*" + DATE_PATTERN_PLAIN + r"\s*$"
TIME_PATTERN = r"^\s*" + TIME_PATTERN_PLAIN + r"\s*$"
DATETIME_PATTERN = r"^\s*" + DATETIME_PATTERN_PLAIN + r"\s*$"
FULL_PATTERN = r"^\s*" + FULL_PATTERN_PLAIN + r"\s*$"

# Mongodb connection uri
MONGO_CONNECTION_URI = "mongodb://localhost:27017/"

# The DB and collection names in MongoDB
DB_NAME = "data"
AIRLINE_DESIGNATOR_DB = DB_NAME
AIRLINE_DESIGNATOR_COLLECTION = "airline_data"

# queue alerts
QUEUE_ALERT_DB = DB_NAME
QUEUE_COLLECTION = "alert_queue"
QUEUE_LISTENER_LOG_PATH = "logs/queue.log"
QUEUE_API_CLIENT_LOG_PATH = "logs/queue_api_client.log"
QUEUE_LISTENER_THREAD_POOL_SIZE = 2
QUEUE_LISTENER_SLEEP_DURATION = 30

# frozen alerts
FROZEN_ALERT_DB = DB_NAME
FROZEN_ALERT_COLLECTION = "frozen_alerts"
FROZEN_LISTENER_LOG_PATH = "logs/frozen.log"
FROZEN_API_CLIENT_LOG_PATH = "logs/frozen_api_client.log"
FROZEN_LISTENER_THREAD_POOL_SIZE = 2
FROZEN_LISTENER_SLEEP_DURATION = 259200

# active alerts
ACTIVE_ALERTS_DB = DB_NAME
ACTIVE_ALERTS_COLLECTION = "active_alerts"
ACTIVE_LISTENER_LOG_PATH = "logs/active.log"
ACTIVE_API_CLIENT_LOG_PATH = "logs/active_api_client.log"
ACTIVE_LISTENER_THREAD_POOL_SIZE = 2
ACTIVE_LISTENER_SLEEP_DURATION = 600
