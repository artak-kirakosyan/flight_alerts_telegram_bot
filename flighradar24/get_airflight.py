
import flight
from helpers import APIClient

import datetime
# flight_list = flight.FlightList("B2734")
#
# flight_list.update()

# cl = APIClient()
# fl = cl.get_flight_by_date("B2734", datetime.datetime(year=2020, month=8, day=23))

al = flight.Alert("B2734", datetime.datetime(year=2020, month=8, day=20))
