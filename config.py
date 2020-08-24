try:
    import re
    import os

except ImportError as e:
    print(f'Error occured during import: {e}')
    print('Please install all necessary libraries and try again')
    exit(1)

#----------------------------------------------#
#         Telegram bot and parse configs       #
#----------------------------------------------#

TG_TOKEN = os.getenv("TG_TOKEN")
FLIGHTSTATS_BASE_URL = "https://www.flightstats.com/v2/flight-tracker"

DATE_PATTERN_STR = "(\d{1,2})[-.,/;:_](\d{1,2})[-.,/;:_](\d{2,4})"
FLIGHT_CODE_PATTERN_STR = "^\s*([A-Z0-9]{2}|[A-Z]{3})\s*([0-9]{1,4})\s*$"

FLIGHT_CODE_PATTERN = re.compile(FLIGHT_CODE_PATTERN_STR)
DATE_PATTERN = re.compile(DATE_PATTERN_STR)
FULL_PATTERN = re.compile(FLIGHT_CODE_PATTERN_STR + "\s*" + DATE_PATTERN_STR)

#----------------------------------------------#
#      airline_designator updater configs      #
#----------------------------------------------#

# Headers and data are for making a request and getting proper result
HEADERS = {
"Host": "www.avcodes.co.uk",
"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0",
"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
"Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
"Content-Type": "application/x-www-form-urlencoded",
"Content-Length": "86",
"Origin": "http://www.avcodes.co.uk",
"Referer": "http://www.avcodes.co.uk/airlcodesearch.asp",
"Upgrade-Insecure-Requests": "1",
}

DATA = {
"status": "Y",
"iataairl": "",
"icaoairl": "",
"account": "",
"prefix": "",
"airlname": "",
"country": "country_name",
"callsign": "",
"B1": "",
}

# First url is for getting the list of current countries
COUNTRIES_URL = "http://www.avcodes.co.uk/airlcodesearch.asp"
# This link is where we get all airline information
AIRLINE_INFO_URL = "http://www.avcodes.co.uk/airlcoderes.asp"

# These detectors are to identifies the rows in the html code where
# iata, icao or full name of the airline is written
# you can update this list to parse more information such as website or iata
# itentifiers
AIRLINE_DESIGNATOR_DETECTORS = {
        "iata": "IATA Code:\xa0",
        "icao": "ICAO Code:\xa0",
        "full_name": "Full Name:",
        }
# A file name where to write the info
AIRLINE_IATA_ICAO_JSON = "airline_iata_icao_codes.json"

# Set write_to_mongo to True to write to mongodb
WRITE_TO_MONGO = True
# Mongodb connection uri
MONGO_CONNECTION_URI = "mongodb://localhost:27017/"
# The DB and collection names in MongoDB
AIRLINE_DESIGNATOR_DB = "data"
AIRLINE_DESIGNATOR_COLLECTION = "airline_data"

# queue alerts
QUEUE_ALERT_DB = "data"
QUEUE_COLLECTION = "alert_queue"

