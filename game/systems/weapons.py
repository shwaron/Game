"""武器数值：等级成长与角色属性绑定加成。"""

STAT_KEYS = ("missing_hp", "hp", "stamina", "mana")


def weapon_level(weapon: dict) -> int:
    max_level = int(weapon.get("max_level", 5))
    return max(1, min(int(weapon.get("level", 1)), max_level))


def level_multiplier(weapon: dict) -> float:
    return 1.0 + float(weapon.get("level_scale", 0.0)) * (weapon_level(weapon) - 1)


def _ratio(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return max(0.0, min(1.0, value / maximum))


def _stat_ratio(stat: str, player) -> float:
    hp = getattr(getattr(player, "health", None), "hp", 0.0)
    max_hp = getattr(getattr(player, "health", None), "max_hp", 0.0)
    if stat == "missing_hp":
        return 1.0 - _ratio(hp, max_hp)
    if stat == "hp":
        return _ratio(hp, max_hp)
    if stat in ("stamina", "mana"):
        pool = getattr(player, stat, None)
        if pool is None:
            return 0.0
        return _ratio(pool.value, pool.max_value)
    return 0.0


def scaling_bonus(weapon: dict, player) -> float:
    total = 0.0
    for entry in weapon.get("scaling", ()):
        stat = entry.get("stat")
        if stat in STAT_KEYS:
            total += float(entry.get("max_bonus", 0.0)) * _stat_ratio(stat, player)
    return total


def weapon_damage(weapon: dict, player) -> float:
    return (
        float(weapon.get("base_damage", 1))
        * level_multiplier(weapon)
        * (1.0 + scaling_bonus(weapon, player))
    )