try:
    from common import get_logger
    from helpers import APIClient, Flight
except ImportError as exception:
    print()
    raise ImportError(f'Error occurred during import: {exception}\n' +
                      'Please install all necessary libraries and try again')


class FlightList:
    def __init__(self, flight_code):
        self.logger = get_logger(logger_name="FLIGHT_LIST", file_name="flight_list.log")
        self.api_client = APIClient()
        self.flight_code = flight_code
        self.flights = {}
        self.logger.info(f"FlightList with flight code {flight_code} has been created")

    def add_or_update_flight(self, flight: Flight):
        if not isinstance(flight, Flight):
            raise ValueError("Specified argument has to be an instance of 'Flight'")

        if flight.flight_code != self.flight_code:
            raise ValueError(f"flight code is different: flight: {flight.flight_code}, list: {self.flight_code}")

        if flight.flight_id not in self.flights:
            self.logger.info("Adding flight to the list.")
            self.flights[flight.flight_id] = flight
        else:
            self.logger.info("Flight already present. Updating it.")
            self.flights[flight.flight_id].update(flight)

    def search_by_departure_date(self, date):
        for flight_id, flight in self.flights.items():
            curr_fl_dep = flight.properties['Scheduled Departure']
            if (curr_fl_dep.year, curr_fl_dep.month, curr_fl_dep.day) == (date.year, date.month, date.day):
                return flight
        return None

    def update_from_api_response(self, flight_list: list):
        for curr_fl in flight_list:
            try:
                curr_flight = Flight.create_from_api_response(curr_fl)
            except ValueError:
                pass
            else:
                self.add_or_update_flight(curr_flight)

    def update(self):
        page = 1
        have_more = True
        while have_more:
            try:
                resp = self.api_client.get_flight(flight_code=self.flight_code, page=page)
            except RuntimeError:
                self.logger.exception(f"Failed to get current page:{page}")
                have_more = False
            else:
                have_more = resp['page']['more']
                current_flights = resp['data']
                if current_flights is None:
                    self.logger.warning(f"No flight data available in page {page}.")
                    have_more = False
                    continue
                self.logger.info(f"Received {len(resp['data'])}, adding to the list")
                self.update_from_api_response(current_flights)
                page += 1


class Alert(Flight):
    def __init__(self, flight_code, date):
        self.api_client = APIClient()
        flight = self.api_client.get_flight_by_date(flight_code=flight_code, date=date)
        if flight is None:
            raise RuntimeError("Flight with current date was not found.")

        super(Alert, self).__init__(
            flight_id=flight.flight_id,
            flight_code=flight.flight_code,
            properties_dict=flight.properties
        )

    def check(self):
        new_flight = self.api_client.get_flight_by_id(flight_code=self.flight_code, flight_id=self.flight_id)
        try:
            diff = self.update(new_flight)
        except (ValueError, TypeError):
            diff = None
        return diff
