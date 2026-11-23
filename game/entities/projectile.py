import pygame

from game import config
from game.systems.combat import TEAM_ENEMY, TEAM_PLAYER


class Projectile:
    _next_uid = 0

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        damage: int,
        team: str,
        size: tuple[int, int] = (6, 3),
        life: float = 3.0,
        gravity: float = 0.0,
    ) -> None:
        self.x = x
        self.y = y
        self.vel_x = vx
        self.vel_y = vy
        self.damage = damage
        self.team = team
        self.w, self.h = size
        self.life = life
        self.gravity = gravity
        self.dead = False
        # id() 会被短命对象复用，命中登记必须用独立序号
        self.uid = Projectile._next_uid
        Projectile._next_uid += 1

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), self.w, self.h)

    def update(self, dt: float, room) -> None:
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        self.vel_y += self.gravity * dt
        self.life -= dt
        if self.life <= 0:
            self.dead = True
            return
        rect = self.rect
        for solid in room.solids:
            if rect.colliderect(solid):
                self.dead = True
                return

    def reflect(self) -> None:
        self.vel_x = -self.vel_x * 1.2
        self.team = TEAM_PLAYER if self.team == TEAM_ENEMY else TEAM_ENEMY

    def draw(self, surface: pygame.Surface) -> None:
        color = config.COLORS["slash"] if self.team == TEAM_PLAYER else config.COLORS["ember"]
        pygame.draw.rect(surface, color, self.rect)