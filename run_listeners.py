from active_listener import ActiveListener
from frozen_listener import FrozenListener
from queue_listener import QueueListener


def main():
    a = ActiveListener()
    f = FrozenListener()
    q = QueueListener()
    a.start()
    f.start()
    q.start()
    a.join()
    q.join()
    f.join()


if __name__ == "__main__":
    main()
