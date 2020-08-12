try:
    import re
    import datetime
    import logging
    import requests

    from bs4 import BeautifulSoup
    import config

except ImportError as e:
    print(f'Error occured during import: {e}')
    print('Please install all necessary libraries and try again')
    exit(1)


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
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return  logger


def validate_flight_code(flight_code: str) -> dict:
    """
        Take in the flight code and try to identify IATA, ICAO and flight num.

        Arguments:
            flight_code: string provided by the user
        Returns:
            data: dictionary of the parse data if any
        Raise ValueError if invalid input
    """
    flight_code = flight_code.upper()
    flight_code = re.match(config.FLIGHT_CODE_PATTERN, flight_code)
    if flight_code is None:
        raise ValueError("Invalid flight number")
    airline_code, flight_number = flight_code.groups()
    data = {}
    data['flight_number'] = flight_number
    if len(airline_code) == 2:
        data['iata'] = airline_code
        data['icao'] = None
    else:
        data['iata'] = None
        data['icao'] = airline_code

    return data


def validate_date(date_str: str) -> datetime.datetime:
    """
        Take in the string date and parse it
        Arguments:
            date_str: string given by the user
        Returns:
            date: datetime object
        Raise ValueError if invalid info provided.
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
    except ValueError as e:
        raise ValueError("Invalid date")
    return date 


def construct_flightstats_url(
        airline_code: str, 
        flight_number: str,
        date: datetime.datetime) -> str:
    """
        This function takes in the necessary info and constructs the flightstats
        URL to be parsed:
        Arguments:
            airline_code: IATA or ICAO designator
            flight_number: 1 to 4 digit flight number
            date: datetime object of the flight date
        Returns:
            url: the url that points to the correct flight from flightstats
    """
    request_components = [config.FLIGHTSTATS_BASE_URL, airline_code, flight_number]
    url = "/".join(request_components)
    url += "?"
    url += f"year={date.year}&"
    url += f"month={date.month}&"
    url += f"date={date.day}&"
    return url


def parse_url_return_soup(url: str) -> BeautifulSoup:
    """
        Parse the url, create BS soup and return
        Arguments:
            url: url to parse
        Returns:
            soup: BeautifulSoup object with the website content
        It raises ValueError if any issues are encountered.
    """
    try:
        resp = requests.get(url)
    except Exception as e:
        raise ValueError(f"Failed to make the request: {e}")
    if not resp.ok:
        raise ValueError(f"Response has error code: {e}")
    
    try:
        soup = BeautifulSoup(resp.text, 'lxml')
    except Exception as e:
        raise ValueError(f"Failed to create the soup: {e}")
    return soup


def parse_flight_stats(url: str) -> dict:
    """
        Take in the url and parse 
        Arguments:
            url: url of the flightstats
        Returns:
            current_state: dictionary of the parsed info
        Raise ValueError if anything wrong
    """
    try:
        soup = parse_url_return_soup(url)
    except ValueError as e:
        raise ValueError(f"{e.args}")
    curr_state = {}
    div_all = soup.find(
            "div", 
            {"class": "ticket__TicketContainer-s1rrbl5o-0 bgrndo"},
            )
    if div_all is None:
        if soup.find(
                "h1",
                {"class": "out-of-date-range__H1-akw3lj-1 eoKbOg"},
                ) is not None:
            curr_state = {"Status": ["Too far from today, check later"]}
        else:
            curr_state = {"Status": ["Something is wrong, check again later"]}
    else:
        div_status = div_all.find(
                "div",
                {"class": "ticket__StatusContainer-s1rrbl5o-17 fWLIvb"},
                )
        if div_status is not None:
            curr_text = div_status.getText(
                    separator=",^,",
                    strip=True)
            curr_state["Current Status"] = curr_text.split(",^,")
        time_divs = div_all.findAll(
                "div",
                {"class": "ticket__TimeGroupContainer-s1rrbl5o-11 ckbilY"}
                )
        time_info = ["Departure", "Arrival"]
        for ind, time_div in enumerate(time_divs):
            curr_text = time_div.getText(separator=",^,", strip=True)
            curr_state[time_info[ind]] = curr_text.split(",^,")
        gate_divs = div_all.findAll(
                "div",
                {"class": "ticket__TerminalGateBagContainer-s1rrbl5o-13 ubbwc"},
                    )
        gate_info = ["Departure Gate", "Arrival Gate"]
        for ind, time_div in enumerate(gate_divs):
            curr_text = time_div.getText(separator=",^,", strip=True)
            curr_state[gate_info[ind]] = curr_text.split(",^,")
    reply = format_the_current_state(curr_state)
    return reply#, div_all, time_div


def format_the_current_state(curr_state: dict) -> str:
    """
        Take the dictionary with necessary info and format it nicely.
        Arguments:
            curr_state: dictionary with current state
        Returns:
            reply: state dictionary nicely formated
    """
    reply = ""
    for st_name, state in curr_state.items():
        reply += st_name + ": "
        for curr_info in state:
            reply += curr_info + " \t"
        reply += "\n"
    return reply


def validate_and_save(flight_data: dict, flight_date: datetime.datetime):
    """
        This function takes in the data user supplied, validates it and saves
        to the mongodb
        Arguments:
            flight_data: dictionary containing flight data
            flight_date: datetime object of the flight date
        Returns:
            curr_state: current state parsed from website
    """
    if datetime.datetime.today() - flight_date > datetime.timedelta(days=3):
        raise ValueError("You have to leave the past to see the future(the date is too old)")

    flight_number = flight_data['flight_number']
    
    # TO-DO: we need to check the following cases:
    #        1. if iata is given, use it and check flightstats
    #        2. if flightstats fails, get icao of the given iata and try again
    #        3. if flightstats fails again, use icao and check flightaware
    # Currently I just use whatever the user gives and use flightstats

    if flight_data['iata'] is not None:
        airline_code = flight_data['iata']
    else:
        airline_code = flight_data['icao']
    flightstats_url = construct_flightstats_url(
                airline_code,
                flight_data['flight_number'],
                flight_date,
                )
    try:
        current_state = parse_flight_stats(flightstats_url)
    except ValueError as e:
        raise ValueError("Failed to parse the info. Please try again later.")
    return current_state
