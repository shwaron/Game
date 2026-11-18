class Health:
    def __init__(self, max_hp: int, armor: int = 0) -> None:
        self.max_hp = max_hp
        self.hp = max_hp
        self.armor = armor

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> bool:
        """Apply damage, return True if this hit was lethal."""
        self.hp = max(0, self.hp - max(0, amount))
        return self.hp <= 0

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + max(0, amount))