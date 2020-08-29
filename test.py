import datetime
from pprint import pprint

from queue_listener import QueueListener
from frozen_listener import FrozenListener

l = QueueListener()

l.frozen_collection.delete_many({})
l.active_collection.delete_many({})
l.queue_collection.delete_many({})

alerts = [
    {
        '_id': '169004254_04_09_2020_NK993',
        'chat_id': 169004254,
        'date': datetime.datetime(2020, 9, 4, 0, 0),
        'flight_code': 'NK993',
    },
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


fr = FrozenListener()
fr.update_one(
    {
        '_id': '169004254_30_08_2020_B2734',
        'chat_id': 169004254,
        'date': datetime.datetime(2020, 8, 30, 0, 0),
        'flight_code': 'B2734',
    },
    fr.frozen_collection,
)
fr.update_one(
    {
        '_id': '169004254_28_08_2020_RM928',
        'chat_id': 169004254,
        'date': datetime.datetime(2020, 8, 28, 0, 0),
        'flight_code': 'RM928',
    },
    fr.frozen_collection,
)
fr.update_one(
    {
        '_id': '169004254_30_08_2020_A2734',
        'chat_id': 169004254,
        'date': datetime.datetime(2020, 8, 30, 0, 0),
        'flight_code': 'A2734',
    },
    fr.frozen_collection,
)

print("BEFORE_______________________________")

print("Frozen:")
pprint(list(fr.frozen_collection.find()))

print("Active:")
pprint(list(fr.active_collection.find()))

fr.listen_to_queue()

print("AFTER_______________________________")
print("Frozen:")
pprint(list(fr.frozen_collection.find()))

print("Active:")
pprint(list(fr.active_collection.find()))
