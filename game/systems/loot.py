import random


def roll_table(table: dict, rng: random.Random | None = None) -> str:
    rng = rng or random
    entries = table["entries"]
    total = sum(entry["weight"] for entry in entries)
    pick = rng.uniform(0, total)
    upto = 0.0
    for entry in entries:
        upto += entry["weight"]
        if pick <= upto:
            return entry["item"]
    return entries[-1]["item"]


def load_tables(data: dict) -> dict[str, dict]:
    return data.get("tables", {})