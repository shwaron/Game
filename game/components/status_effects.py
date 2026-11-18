DOT_EFFECTS = {"burn", "poison", "bleed"}


class StatusEffects:
    def __init__(self) -> None:
        self.effects: dict[str, dict] = {}

    def apply(
        self,
        name: str,
        duration: float,
        potency: float = 0.0,
        max_stacks: int = 1,
    ) -> None:
        effect = self.effects.setdefault(
            name, {"time": 0.0, "potency": 0.0, "stacks": 0}
        )
        effect["stacks"] = min(max_stacks, effect["stacks"] + 1)
        effect["potency"] = potency
        effect["time"] = max(effect["time"], duration)

    def has(self, name: str) -> bool:
        return name in self.effects

    def update(self, dt: float) -> float:
        """Tick timers, return total damage-per-second * dt from DOT effects."""
        damage = 0.0
        expired = []
        for name, effect in self.effects.items():
            if name in DOT_EFFECTS:
                damage += effect["potency"] * effect["stacks"] * dt
            effect["time"] -= dt
            if effect["time"] <= 0:
                expired.append(name)
        for name in expired:
            del self.effects[name]
        return damage

    def speed_multiplier(self) -> float:
        return 0.5 if self.has("freeze") else 1.0

    @property
    def stunned(self) -> bool:
        return self.has("stun")

    def absorb(self, amount: float) -> float:
        """Shield-style absorption, return remaining damage after absorption."""
        shield = self.effects.get("shield")
        if not shield:
            return amount
        absorbed = min(shield["potency"], amount)
        shield["potency"] -= absorbed
        if shield["potency"] <= 0:
            del self.effects["shield"]
        return amount - absorbed