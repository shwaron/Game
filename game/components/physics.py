import pygame


class PhysicsBody:
    def __init__(self, x: float, y: float, w: int, h: int) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.ground_is_one_way = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), self.w, self.h)

    def move_and_collide(
        self,
        dt: float,
        solids: list[pygame.Rect],
        one_ways: list[pygame.Rect],
        drop_through: bool = False,
    ) -> None:
        self.x += self.vel_x * dt
        rect = self.rect
        for solid in solids:
            if rect.colliderect(solid):
                if self.vel_x > 0:
                    self.x = float(solid.left - self.w)
                elif self.vel_x < 0:
                    self.x = float(solid.right)
                self.vel_x = 0.0
                rect = self.rect

        prev_bottom = rect.bottom
        self.y += self.vel_y * dt
        rect = self.rect
        self.on_ground = False
        self.ground_is_one_way = False
        if self.vel_y >= 0:
            probe = pygame.Rect(rect.x, rect.y, rect.w, rect.h + 1)
            for solid in solids:
                if probe.colliderect(solid) and prev_bottom <= solid.top + 1:
                    self.y = float(solid.top - self.h)
                    self.vel_y = 0.0
                    self.on_ground = True
                    rect = self.rect
                    probe = pygame.Rect(rect.x, rect.y, rect.w, rect.h + 1)
            if not drop_through:
                for platform in one_ways:
                    if (
                        prev_bottom <= platform.top + 1
                        and probe.colliderect(platform)
                    ):
                        self.y = float(platform.top - self.h)
                        self.vel_y = 0.0
                        self.on_ground = True
                        self.ground_is_one_way = True
                        rect = self.rect
                        probe = pygame.Rect(rect.x, rect.y, rect.w, rect.h + 1)
        else:
            for solid in solids:
                if rect.colliderect(solid):
                    self.y = float(solid.bottom)
                    self.vel_y = 0.0
                    rect = self.rect