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

# alerts DB
ALERT_DB = DB_NAME
ALERT_COLLECTION = "alerts"

QUEUE_LISTENER_LOG_PATH = "logs/queued_alerts.log"
QUEUE_LISTENER_THREAD_POOL_SIZE = 3
QUEUE_API_CLIENT_LOG_PATH = "logs/queued_api.log"

ACTIVE_LISTENER_LOG_PATH = "logs/active_alerts.log"
ACTIVE_LISTENER_THREAD_POOL_SIZE = 3
ACTIVE_API_CLIENT_LOG_PATH = "logs/queued_api.log"

