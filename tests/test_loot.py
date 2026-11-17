import random

from game.systems.loot import roll_table


def test_single_entry_always_wins():
    table = {"entries": [{"item": "fire_seed", "weight": 5}]}
    for _ in range(20):
        assert roll_table(table, random.Random(3)) == "fire_seed"


def test_zero_weight_never_selected():
    table = {
        "entries": [
            {"item": "never", "weight": 0},
            {"item": "always", "weight": 10},
        ]
    }
    rng = random.Random(7)
    for _ in range(200):
        assert roll_table(table, rng) == "always"


def test_weights_bias_result():
    table = {
        "entries": [
            {"item": "common", "weight": 70},
            {"item": "rare", "weight": 30},
        ]
    }
    rng = random.Random(123)
    results = [roll_table(table, rng) for _ in range(1000)]
    assert 600 < results.count("common") < 800