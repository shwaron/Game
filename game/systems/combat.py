import random

TEAM_PLAYER = "player"
TEAM_ENEMY = "enemy"


def roll_damage(
    base_damage: float,
    armor: int = 0,
    bonus: float = 0.0,
    crit_chance: float = 0.0,
    rng: random.Random | None = None,
    crit_multiplier: float = 1.5,
) -> tuple[int, bool]:
    rng = rng or random
    crit = rng.random() < crit_chance
    damage = base_damage * (1.0 + bonus)
    if crit:
        damage *= crit_multiplier
    return max(1, int(round(damage - armor))), crit


class CombatSystem:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self._hurtboxes: list = []
        self._swings: dict[str, set[int]] = {}

    def register(self, entity) -> None:
        if entity not in self._hurtboxes:
            self._hurtboxes.append(entity)

    def unregister(self, entity) -> None:
        if entity in self._hurtboxes:
            self._hurtboxes.remove(entity)

    def resolve_melee(
        self,
        swing_key: str,
        rect,
        team: str,
        base_damage: float,
        knockback: float = 0.0,
        source_pos: tuple[float, float] | None = None,
        bonus: float = 0.0,
        crit_chance: float = 0.0,
    ) -> list[tuple[object, int, bool]]:
        if len(self._swings) > 512:
            self._swings.clear()
        hit_ids = self._swings.setdefault(swing_key, set())
        hits = []
        for target in list(self._hurtboxes):
            if target.team == team or not target.health.alive:
                continue
            if id(target) in hit_ids:
                continue
            if rect.colliderect(target.rect):
                amount, crit = roll_damage(
                    base_damage,
                    target.health.armor,
                    bonus,
                    crit_chance,
                    self.rng,
                )
                hit_ids.add(id(target))
                target.on_hit(amount, source_pos, knockback)
                hits.append((target, amount, crit))
        return hits