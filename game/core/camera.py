import pygame


class Camera:
    """Smooth horizontal follow camera clamped to the room bounds."""

    def __init__(
        self,
        view_w: int,
        view_h: int,
        follow_speed: float = 7.0,
        look_ahead: float = 24.0,
    ) -> None:
        self.view_w = view_w
        self.view_h = view_h
        self.follow_speed = follow_speed
        self.look_ahead = look_ahead
        self.x = 0.0
        self.y = 0.0

    @property
    def offset(self) -> tuple[int, int]:
        return -round(self.x), -round(self.y)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), self.view_w, self.view_h)

    def snap(self, target: pygame.Rect, world_w: int, world_h: int) -> None:
        self.x = self._clamp(target.centerx - self.view_w / 2, world_w, self.view_w)
        self.y = self._clamp(target.centery - self.view_h / 2, world_h, self.view_h)

    def update(
        self,
        dt: float,
        target: pygame.Rect,
        world_w: int,
        world_h: int,
        facing: int = 1,
    ) -> None:
        desired_x = (
            target.centerx
            - self.view_w / 2
            + self.look_ahead * (1 if facing >= 0 else -1)
        )
        desired_y = target.centery - self.view_h / 2
        desired_x = self._clamp(desired_x, world_w, self.view_w)
        desired_y = self._clamp(desired_y, world_h, self.view_h)
        t = min(1.0, dt * self.follow_speed)
        self.x += (desired_x - self.x) * t
        self.y += (desired_y - self.y) * t

    @staticmethod
    def _clamp(value: float, world_size: int, view_size: int) -> float:
        limit = max(0.0, float(world_size - view_size))
        return max(0.0, min(value, limit))
