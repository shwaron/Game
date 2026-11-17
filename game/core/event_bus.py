from collections import defaultdict


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list] = defaultdict(list)

    def subscribe(self, event_name: str, callback) -> None:
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback) -> None:
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, payload: dict) -> None:
        for callback in list(self._subscribers[event_name]):
            callback(dict(payload))