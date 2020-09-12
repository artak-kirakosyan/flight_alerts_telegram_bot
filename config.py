try:
    import re
    import os

except ImportError as e:
    raise ImportError(f'Error occurred during import: {e}\
    Please install all necessary libraries and try again')

# Telegram bot and parse configs
TG_TOKEN = os.getenv("TG_TOKEN")
BOT_LOG_PATH = "logs/bot.log"


DATE_PATTERN_STR = r"(\d{1,2})[-.,/;:_](\d{1,2})[-.,/;:_](\d{2,4})"
TIME_PATTERN_STR = None
FLIGHT_CODE_PATTERN_STR = r"^\s*([A-Z0-9]{2}|[A-Z]{3})\s*([0-9]{1,4})\s*$"

FLIGHT_CODE_PATTERN = re.compile(FLIGHT_CODE_PATTERN_STR)
DATE_PATTERN = re.compile(DATE_PATTERN_STR)
FULL_PATTERN = re.compile(FLIGHT_CODE_PATTERN_STR + r"\s*" + DATE_PATTERN_STR)


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
