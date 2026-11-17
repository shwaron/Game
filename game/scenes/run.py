from types import SimpleNamespace

import pygame

from game import config
from game.core.scene_manager import Scene
from game.entities.player import Player


class PracticeScene(Scene):
    def __init__(self, game) -> None:
        self.game = game
        self.room = SimpleNamespace(
            solids=[
                pygame.Rect(0, 246, 480, 24),
                pygame.Rect(0, 0, 8, 270),
                pygame.Rect(472, 0, 8, 270),
                pygame.Rect(0, 0, 480, 8),
                pygame.Rect(352, 206, 64, 40),
            ],
            one_ways=[
                pygame.Rect(120, 190, 96, 8),
                pygame.Rect(270, 148, 96, 8),
                pygame.Rect(60, 106, 80, 8),
            ],
        )
        self.player = Player(48, 200)
        self.dummy = pygame.Rect(300, 214, 20, 32)
        self.dummy_flash = 0.0
        self.hitstop = 0.0
        self._font = None
        self._font_small = None

    def enter(self) -> None:
        self._font = pygame.font.Font(None, 14)
        self._font_small = pygame.font.Font(None, 11)

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.is_action_just_pressed("pause"):
            self.game.quit()
            return
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        self.player.update(dt, inp, self.room)
        hitbox = self.player.attack_hitbox
        if (
            hitbox
            and not self.player.attack_hit
            and hitbox.colliderect(self.dummy)
        ):
            self.player.attack_hit = True
            self.dummy_flash = 0.15
            self.hitstop = config.HITSTOP_ON_HIT
        self.dummy_flash = max(0.0, self.dummy_flash - dt)

    def draw(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        surface.fill(c["bg"])
        for rect in self.room.solids:
            pygame.draw.rect(surface, c["terrain"], rect)
            pygame.draw.rect(surface, c["terrain_top"], (rect.x, rect.y, rect.w, 2))
        for rect in self.room.one_ways:
            pygame.draw.rect(surface, c["one_way"], rect)

        dummy_color = c["dummy_flash"] if self.dummy_flash > 0 else c["dummy"]
        pygame.draw.rect(surface, dummy_color, self.dummy)
        pygame.draw.rect(surface, c["bg"], (self.dummy.x + 4, self.dummy.y + 6, 4, 4))
        pygame.draw.rect(surface, c["bg"], (self.dummy.x + 12, self.dummy.y + 6, 4, 4))

        self.player.draw(surface)
        self._draw_hud(surface)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        p = self.player
        dash = "ready" if p.dash_cooldown <= 0 else f"{p.dash_cooldown:.2f}s"
        line = (
            f"FPS {self.game.clock.get_fps():.0f}   state {p.state}   "
            f"dash {dash}   pos ({p.rect.x}, {p.rect.y})"
        )
        surface.blit(self._font.render(line, True, c["hud"]), (12, 12))
        hint = "A/D move   SPACE jump   S+SPACE drop   SHIFT dash   J attack   ESC quit"
        surface.blit(self._font_small.render(hint, True, c["hud_dim"]), (12, 258))