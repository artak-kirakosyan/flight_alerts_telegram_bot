from queue_listener import Listener

import datetime
from pprint import pprint

l = Listener()

l.frozen_collection.delete_many({})
l.active_collection.delete_many({})
l.queue_collection.delete_many({})

alerts = [
    {
        '_id': '169004254_29_08_2020_B2734',
        'chat_id': 169004254,
        'date': datetime.datetime(2020, 8, 29, 0, 0),
        'flight_code': 'B2734',
    },
    {
        '_id': '169004254_15_08_2020_A2734',
        'chat_id': 169004254,
        'date': datetime.datetime(2020, 8, 15, 0, 0),
        'flight_code': 'A2734',
    },
    {
        '_id': '169004254_15_09_2020_B2834',
        'chat_id': 169004254,
        'date': datetime.datetime(2020, 9, 15, 0, 0),
        'flight_code': 'B2834',
    },
]

l.queue_collection.insert_many(alerts)
print("BEFORE_______________________________")
print("Queue:")
pprint(list(l.queue_collection.find()))

print("Frozen:")
pprint(list(l.frozen_collection.find()))

print("Active:")
pprint(list(l.active_collection.find()))

l.listen_to_queue()

print("AFTER_________________________")
print("Queue:")
pprint(list(l.queue_collection.find()))

print("Frozen:")
pprint(list(l.frozen_collection.find()))

print("Active:")
pprint(list(l.active_collection.find()))
