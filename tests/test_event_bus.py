from game.core.event_bus import EventBus


def test_publish_delivers_payload_copy():
    bus = EventBus()
    received = []
    bus.subscribe("player.damaged", received.append)
    payload = {"amount": 10}
    bus.publish("player.damaged", payload)
    assert received == [{"amount": 10}]
    received[0]["amount"] = 999
    assert payload["amount"] == 10


def test_unsubscribe_stops_delivery():
    bus = EventBus()
    received = []
    bus.subscribe("enemy.killed", received.append)
    bus.unsubscribe("enemy.killed", received.append)
    bus.publish("enemy.killed", {"enemy_id": "rat"})
    assert received == []


def test_multiple_subscribers_each_get_copy():
    bus = EventBus()
    a, b = [], []
    bus.subscribe("ui.notify", a.append)
    bus.subscribe("ui.notify", b.append)
    bus.publish("ui.notify", {"text_key": "x"})
    a[0]["text_key"] = "y"
    assert b[0]["text_key"] == "x"