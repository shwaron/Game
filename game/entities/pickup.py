import pygame

from game import config

FIRE_SEED = "fire_seed"
POTION = "potion"
MANUAL = "manual"
EMBER_VALUE = 3
POTION_HEAL = 20


class Pickup:
    def __init__(self, item_id: str, x: float, y: float) -> None:
        self.item_id = item_id
        self.x = x
        self.y = y
        self.w = 10
        self.h = 10
        self.vel_y = 0.0
        self.landed = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), self.w, self.h)

    @property
    def collect_rect(self) -> pygame.Rect:
        return self.rect.inflate(12, 12)

    def update(self, dt: float, room) -> None:
        if self.landed:
            return
        self.vel_y = min(self.vel_y + 600 * dt, 300)
        self.y += self.vel_y * dt
        rect = self.rect
        for solid in room.solids:
            if rect.colliderect(solid):
                self.y = float(solid.top - self.h)
                self.landed = True
                self.vel_y = 0.0
                break

    def draw(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        r = self.rect
        if self.item_id == FIRE_SEED:
            pygame.draw.rect(surface, c["ember"], r)
            pygame.draw.rect(surface, c["slash"], (r.x + 3, r.y + 3, 3, 3))
        elif self.item_id == MANUAL:
            pygame.draw.rect(surface, (206, 174, 114), r)
            pygame.draw.rect(surface, (236, 208, 150), (r.x + 1, r.y + 1, r.w - 2, 2))
            pygame.draw.rect(surface, (150, 48, 40), (r.x + 4, r.y + 2, 2, r.h - 3))
            pygame.draw.rect(surface, (96, 70, 42), (r.x, r.y + 3, r.w, 1))
            pygame.draw.rect(surface, (96, 70, 42), (r.x, r.y + 6, r.w, 1))
        else:
            pygame.draw.rect(surface, (120, 200, 140), r)
            pygame.draw.rect(surface, (230, 240, 230), (r.x + 3, r.y - 2, 4, 3))