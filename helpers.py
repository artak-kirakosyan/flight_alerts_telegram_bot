try:
    import re
    import datetime
    import logging
    import requests

    from pymongo import MongoClient, UpdateOne
    from pymongo.collection import Collection
    from pymongo.errors import PyMongoError
    from telegram import Bot

    import config

except ImportError as exc:
    raise ImportError(f'Error occurred during import: {exc}\
    \nPlease install all necessary libraries and try again')


def get_logger(
        logger_name=__name__, 
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
    file_handler.setFormatter(file_formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)

    logger = logging.getLogger(name=logger_name)
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def get_collection(connection_uri: str, db_name: str, collection_name: str) -> Collection:
    client = MongoClient(connection_uri)
    db = client.get_database(name=db_name)
    coll = db.get_collection(collection_name)
    return coll


def process_flight_code(flight_code: str, airline_designator_collection: Collection) -> dict:
    """
        Take in the flight code and try to identify IATA, ICAO and flight num.

        Arguments:
            flight_code: string provided by the user
            airline_designator_collection: pymongo collection object where airline designators are stored
        Returns:
            data: dictionary of the parse data if any
        Raise ValueError if invalid input
    """
    flight_code = flight_code.upper()
    flight_code = re.match(config.FLIGHT_CODE_PATTERN, flight_code)
    if flight_code is None:
        raise ValueError("Could not identify flight code. Make sure you entered everything correctly.")
    airline_code, flight_number = flight_code.groups()
    data = {'flight_number': flight_number}
    if len(airline_code) == 2:
        data['iata'] = airline_code
        data['icao'] = None
    else:
        data['iata'] = None
        data['icao'] = airline_code

    if data['iata'] is None:
        airlines = airline_designator_collection.find(
            {
                "icao": data['icao'],
            }
        )
    else:
        airlines = airline_designator_collection.find(
            {
                "iata": data['iata'],
            }
        )
    try:
        airlines = list(airlines)
    except PyMongoError:
        reply = "There was an error, please try again later."
        raise ValueError(reply)

    if len(airlines) == 0:
        reply = "Hmm, I cant find the flight info you asked for :/"
        raise ValueError(reply)
    else:
        data['iata'] = airlines[0]['iata']
    data['flight_code'] = data['iata'] + data['flight_number']
    return data


def process_date(date_str: str) -> datetime.datetime:
    """
        Take in the string date and parse it
        Arguments:
            date_str: string given by the user
        Returns:
            date: datetime object
        Raise ValueError if invalid info provided.
        Raise
    """
    match = re.search(config.DATE_PATTERN, date_str)
    if match is None:
        raise ValueError("Invalid format for date.")
    day, month, year = match.groups()
    try:
        year = int(year)
        month = int(month)
        day = int(day)
        if year < 100:
            year += 2000
        date = datetime.datetime(year=year, month=month, day=day)
    except ValueError:
        raise ValueError("Invalid date")

    if datetime.datetime.today() - date > datetime.timedelta(days=2):
        raise ValueError("Date is too old")
    return date


def validate_queue_and_inform_user(
        user_data: dict,
        queue_collection: Collection,
        bot: Bot):
    """
        This function takes in the data user supplied, validates it and saves to the mongodb
        Arguments:
            user_data: dictionary containing flight codes, date and chat_id
            queue_collection: pymongo collection object where to queue the alert
            bot: telegram.bot object which will inform the user about the queue writing results.
        Returns: None
    """
    alert_id = "_".join(
        [
            str(user_data['chat_id']),
            user_data['date'].strftime("%d_%m_%Y"),
            user_data['flight_data']['flight_code'],
        ]
    )
    alert_dict = {
        "_id": alert_id,
        "date": user_data['date'],
        "flight_code": user_data['flight_data']['flight_code'],
        "chat_id": user_data['chat_id']
    }

    try:
        response = queue_collection.update_one(
            {"_id": alert_id},
            {"$set": alert_dict},
            upsert=True,
        )
    except PyMongoError:
        reply = "Something went wrong. Please try again later."
    else:
        if response.acknowledged:
            reply = "Alert is in queue. Will update shortly."
        else:
            reply = "Something went wrong. Please try again later."
    bot.send_message(
        chat_id=user_data['chat_id'],
        text=reply,
    )


class Flight:
    """
    Class representing a flight
    """
    def __init__(self, flight_id, flight_code, properties_dict):
        """
        Constructor of the flight
        :param flight_id: flight ID given by flightradar24 API
        :param flight_code: flight code comprised of airline code and flight number
        :param properties_dict: a dictionary containing all available info about the flight
        """
        self.flight_id = flight_id
        self.flight_code = flight_code
        self.properties = properties_dict.copy()

    @classmethod
    def from_dict(cls, flight_dict):
        """
        Alternative constructor to create the instance from dictionary
        :param flight_dict:
        :return: instance of Flight with properties taken from flight_dict
        """
        flight_id = flight_dict['flight_id']
        flight_code = flight_dict['flight_code']
        properties = flight_dict['properties']
        return cls(flight_id=flight_id, flight_code=flight_code, properties_dict=properties)

    def to_dict(self):
        """
        Create and return the dictionary with all information about the flight
        :return: dictionary with all the information needed
        """
        flight_dict = {
            'flight_id': self.flight_id,
            'flight_code': self.flight_code,
            'properties': self.properties,
        }
        return flight_dict

    @classmethod
    def create_from_api_response(cls, flight_dict):
        """
        This is another alternative constructor. Supply the instance of the flightradar24 API response.
        1 flight at a time.
        :param flight_dict: a dictionary containing information about a single flight
        :return: an instance of Flight.
        Raises ValueError if flight_id or flight_code is missing.
        """
        try:
            flight_id = flight_dict['identification']['row']
        except KeyError:
            raise ValueError("No identification in the json file.")

        try:
            flight_code = flight_dict['identification']['number']['default']
        except KeyError:
            raise ValueError("No flight code in the json file.")

        try:
            curr_status = flight_dict['status']['text']
        except KeyError:
            curr_status = None

        try:
            scheduled_dep = datetime.datetime.fromtimestamp(flight_dict['time']['scheduled']['departure'])
        except TypeError:
            scheduled_dep = None
        except KeyError:
            scheduled_dep = None

        try:
            scheduled_arr = datetime.datetime.fromtimestamp(flight_dict['time']['scheduled']['arrival'])
        except TypeError:
            scheduled_arr = None
        except KeyError:
            scheduled_arr = None

        try:
            real_dep = datetime.datetime.fromtimestamp(flight_dict['time']['real']['departure'])
        except TypeError:
            real_dep = None
        except KeyError:
            real_dep = None

        try:
            real_arr = datetime.datetime.fromtimestamp(flight_dict['time']['real']['arrival'])
        except TypeError:
            real_arr = None
        except KeyError:
            real_arr = None

        try:
            estimated_dep = datetime.datetime.fromtimestamp(flight_dict['time']['estimated']['departure'])
        except TypeError:
            estimated_dep = None
        except KeyError:
            estimated_dep = None

        try:
            estimated_arr = datetime.datetime.fromtimestamp(flight_dict['time']['estimated']['arrival'])
        except TypeError:
            estimated_arr = None
        except KeyError:
            estimated_arr = None

        properties_dict = {
            "Current Status": curr_status,
            "Scheduled Departure": scheduled_dep,
            "Real Departure": real_dep,
            "Estimated Departure": estimated_dep,
            "Scheduled Arrival": scheduled_arr,
            "Real Arrival": real_arr,
            "Estimated Arrival": estimated_arr,
        }
        flight = cls(flight_id=flight_id, flight_code=flight_code, properties_dict=properties_dict)
        return flight

    def _validate_other(self, other):
        """
        A helper function to check if other is a valid Flight or not.
        A flight is considered valid, if
            1. it is an instance of the class Flight,
            2. the list of properties the other and self have are the same
            3. the flight_id and flight_code are equal for self and other.
        :param other: an instance of Flight
        :return: None
        Raise TypeError if other is not an instance of Flight and ValueError if it is not valid for any other reason.
        """
        if not isinstance(other, Flight):
            raise TypeError("Other should be an instance of Flight class.")

        if self.properties.keys() != other.properties.keys():
            raise ValueError("Properties of self and other did not match.")

        if self.flight_id != other.flight_id or self.flight_code != self.flight_code:
            raise ValueError("Self and other are different flights!")

        # This part of the code is likely to be useless as we have None for missing dates. When they appear, the types
        # will differ, which is not good for us.
        # for prop_name, prop in self.properties.items():
        #     other_prop = other.properties[prop_name]
        #     if type(other_prop) != type(prop):
        #         raise ValueError(f"The type of the {prop_name} is different for self and other.")

    def _compare(self, other):
        """
        Validate and compare the self and other. Return a dictionary of the differences of the following form:
            {"property_name": [self_value, other_value]}
        :param other: an instance of Flight to be compared with self
        :return: dictionary with differences
        """
        self._validate_other(other)
        diff_dict = {}
        for prop_name, prop in self.properties.items():
            other_property = other.properties[prop_name]
            if other_property != prop:
                # print(f"Difference in {prop_name}, self:{prop}, other:{other_property}")
                diff_dict[prop_name] = [prop, other_property]
        return diff_dict

    def update(self, other):
        """
        Compare the other with self and update self if it is different from other.
        :param other: an instance of Flight from which self will be updated
        :return: dictionary with differences present
        """
        diff_dict = self._compare(other)
        for prop_name, prop in diff_dict.items():
            self.properties[prop_name] = prop[1]
        return diff_dict

    def __str__(self):
        """
        Return the string representation of the flight
        :return: string showing all information about the flight
        """
        res = ""
        res += f"Flight: {self.flight_code}\n"
        res += f"ID: {self.flight_id}"
        for prop_name, prop in self.properties.items():
            if prop is None:
                prop = ""
            res += f"\n{prop_name}: {prop}"
        return res


class Alert:
    """
    A class representing an alert.
    """
    def __init__(self, flight: Flight, chat_id: int, alert_id: str):
        """
        Construct an alert.
        Arguments:
            flight: A Flight object representing the flight
            chat_id: the ID of the chat who requested the alert
            alert_id: the ID of the alert comprised of the chat_id, flight code and flight date
        """
        self.flight = flight
        self.chat_id = chat_id
        self.alert_id = alert_id

    def to_dict(self):
        """
        Return the dictionary representation of the alert.
        Arguments: None
        Returns:
            dictionary containing all info about the flight and alert
        """
        res_dict = {
            "_id": self.alert_id,
            "flight": self.flight.to_dict(),
            'chat_id': self.chat_id,
        }
        return res_dict

    @classmethod
    def from_dict(cls, alert_dict):
        """
        An alternative constructor to create the alert from the dictionary representation
        Arguments:
            alert_dict: dictionary which contains the alert_id, Flight's dictionary and chat_id
        """
        alert_id = alert_dict['_id']
        flight = Flight.from_dict(alert_dict['flight'])
        chat_id = alert_dict['chat_id']
        return cls(flight=flight, chat_id=chat_id, alert_id=alert_id)


class APIClient:
    """
    A helper class to interact with the API of the flightradar24.
    """
    def __init__(self, proxies=None):
        """
        Constructor.
        :param proxies: list of proxies to be supplied to the request methods. Defaults to None
        """
        self.logger = get_logger(logger_name="API_CLIENT", file_name=config.API_CLIENT_LOG_PATH)
        self.request_base_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0"
        }
        self.proxies = proxies
        self.balance_json_url = 'https://www.flightradar24.com/balance.json'
        self.api_url = 'https://api.flightradar24.com/common/v1'
        self.flight_url = "/flight/list.json?&fetchBy=flight&page={}&limit=100&query={}"
        self.logger.info("API Client created")

    def make_request(self, end_point, proxies=None):
        """
        Make the request and return the JSON of the response if successful.
        If any errors occur during the request or the error code is not ok, raise RuntimeError.
        :param end_point: the url of the endpoint which should be accessed.
        :param proxies: list of alternative proxies. Defaults to None. If None, the self.proxies will be used.
        :return: dictionary of the response
        """
        if proxies is None:
            proxies = self.proxies
        try:
            self.logger.info(f"Requesting '{end_point}'")
            r = requests.get(end_point, headers=self.request_base_headers, proxies=proxies)
        except requests.RequestException as e:
            self.logger.exception("Exception occurred during request:")
            raise RuntimeError(f"Error in request: {e}")

        if not r.ok:
            self.logger.error(f"Status code is not ok: {r.status_code}")
            raise RuntimeError(f"Request failed: {r.status_code}")
        return r.json()

    def get_flight(self, flight_code, page=1):
        """
        Query the API using the flight code
        :param flight_code: flight code containing airline code and flight number
        :param page: which page we are trying to access
        :return: return the response component from the result component if request was successful.
        Raises ValueError if the appropriate information is not found in the response.
        """
        endpoint = self.api_url + self.flight_url.format(page, flight_code)
        resp = self.make_request(endpoint)
        try:
            response = resp['result']['response']
        except KeyError:
            self.logger.exception(f"Response does not contain any info: {resp}")
            raise ValueError("No results were found")
        return response

    def get_flight_by_id(self, flight_code, flight_id):
        """
        Query the API using the flight id and flight code
        :param flight_code: flight code containing airline code and flight number
        :param flight_id: flight id given by the flightradar24 API
        :return: Flight object created from the found flight data. None if not found.
        """
        resp = self.get_flight(flight_code)
        current_flights = resp['data']
        if current_flights is not None:
            self.logger.info("Current request contains flight data, processing it")
            for flight in current_flights:
                curr_flight = Flight.create_from_api_response(flight)
                if curr_flight.flight_id == flight_id:
                    self.logger.info("Flight with specified flight_id is found, returning it.")
                    return curr_flight
        self.logger.warning("Flight with specified flight_id not found, returning None")
        return None

    def get_flight_by_date(self, flight_code, date):
        """
        Query the API using the flight code and date.
        :param flight_code: flight code containing airline code and flight number
        :param date: a datetime object with the requested flight departure date.
            Should be in local time zone of the flight.
        :return: Flight object created from the found flight data. None if not found.
        """
        try:
            resp = self.get_flight(flight_code)
        except ValueError:
            self.logger.exception("No results found at all")
            raise ValueError("No results found at all")
        current_flights = resp['data']
        if current_flights is not None:
            self.logger.info("Current request contains flight data, processing it")
            for flight in current_flights:
                curr_flight = Flight.create_from_api_response(flight)
                curr_fl_dep = curr_flight.properties['Scheduled Departure']
                if (curr_fl_dep.year, curr_fl_dep.month, curr_fl_dep.day) == (date.year, date.month, date.day):
                    self.logger.info("Flight with specified date is found, returning it.")
                    return curr_flight
        self.logger.warning("Flight with specified date not found, returning None")
        return None
