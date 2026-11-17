class ResourcePool:
    def __init__(
        self,
        max_value: float,
        regen_rate: float = 0.0,
        regen_delay: float = 0.0,
    ) -> None:
        self.max_value = float(max_value)
        self.value = float(max_value)
        self.regen_rate = regen_rate
        self.regen_delay = regen_delay
        self._regen_timer = 0.0

    def update(self, dt: float) -> None:
        self._regen_timer = max(0.0, self._regen_timer - dt)
        if self._regen_timer <= 0 and self.value < self.max_value:
            self.value = min(self.max_value, self.value + self.regen_rate * dt)

    def can_spend(self, amount: float) -> bool:
        return self.value >= amount

    def spend(self, amount: float) -> bool:
        if not self.can_spend(amount):
            return False
        self.value -= amount
        self._regen_timer = self.regen_delay
        return True

    def refill(self) -> None:
        self.value = self.max_value
        self._regen_timer = 0.0