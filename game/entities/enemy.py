import pygame

from game import config
from game.components.health import Health
from game.components.physics import PhysicsBody
from game.components.status_effects import StatusEffects
from game.core.animation import Animator
from game.systems.combat import TEAM_ENEMY


class Enemy:
    def __init__(
        self,
        enemy_id: str,
        x: float,
        y: float,
        data: dict,
        room,
        anim_clips: dict | None = None,
    ) -> None:
        self.enemy_id = enemy_id
        self.anim = Animator(anim_clips) if anim_clips else None
        self.data = data
        self.room = room
        self.team = TEAM_ENEMY
        self.body = PhysicsBody(x, y, 20, 34)
        self.health = Health(data["hp"], data.get("armor", 0))
        self.status = StatusEffects()
        self.attack = data["attacks"][0]
        self.state = "idle"
        self.state_timer = 0.0
        self.cooldown = 0.8
        self.facing = -1
        self.hit_flash = 0.0
        self.dead_timer = 0.4
        self.death_reported = False
        self.swing_id = 0
        self.pending_projectile: dict | None = None
        self._dot_pool = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect

    @property
    def attack_hitbox(self) -> pygame.Rect | None:
        if self.state != "active" or "hitbox" not in self.attack:
            return None
        w, h = self.attack["hitbox"]
        r = self.body.rect
        x = r.right if self.facing > 0 else r.left - w
        return pygame.Rect(x, r.centery - h // 2, w, h)

    def on_hit(self, amount: int, source_pos, knockback: float) -> None:
        if not self.health.alive:
            return
        lethal = self.health.take_damage(amount)
        self.hit_flash = 0.12
        if lethal:
            self.state = "dead"
            self.body.vel_x = 0.0
            return
        if knockback:
            r = self.body.rect
            direction = -1 if source_pos and source_pos[0] > r.centerx else 1
            self.body.vel_x = direction * knockback
            self.body.vel_y = -70.0
        self.state = "stagger"
        self.state_timer = 0.18

    def stagger(self, duration: float) -> None:
        self.state = "stagger"
        self.state_timer = duration

    def update(self, dt: float, player) -> None:
        if not self.health.alive:
            self.state = "dead"
            self.dead_timer -= dt
            self._physics(dt)
            self._update_animation(dt)
            return

        dot = self.status.update(dt)
        if dot > 0:
            self._dot_pool += dot
            whole = int(self._dot_pool)
            if whole > 0:
                self._dot_pool -= whole
                self.health.take_damage(whole)
                if not self.health.alive:
                    self.state = "dead"
                    return

        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.cooldown = max(0.0, self.cooldown - dt)

        if self.state == "stagger":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "idle"
        elif self.state in ("windup", "active", "recovery"):
            self._advance_attack(dt)
        elif not self.status.stunned:
            self._think(dt, player)
        else:
            self.body.vel_x = 0.0

        if self.state in ("windup", "active", "recovery"):
            self.body.vel_x = 0.0
        self._physics(dt)
        self._update_animation(dt)

    def _update_animation(self, dt: float) -> None:
        if not self.anim:
            return
        if not self.health.alive:
            name = "death"
        elif self.state == "stagger":
            name = "stagger"
        elif self.state in ("windup", "active", "recovery"):
            name = self.state
        elif abs(self.body.vel_x) > 5:
            name = "walk"
        else:
            name = "idle"
        self.anim.play(name)
        self.anim.update(dt)

    def _advance_attack(self, dt: float) -> None:
        self.state_timer -= dt
        if self.state_timer > 0:
            return
        if self.state == "windup":
            self.state = "active"
            self.state_timer = self.attack["active_ms"] / 1000.0
            self.swing_id += 1
        elif self.state == "active":
            self.state = "recovery"
            self.state_timer = self.attack["recovery_ms"] / 1000.0
        else:
            self.state = "idle"
            self.cooldown = self.attack.get("cooldown", 1.2)

    def _physics(self, dt: float) -> None:
        self.body.vel_y = min(
            self.body.vel_y + config.GRAVITY * dt, config.MAX_FALL
        )
        if self.body.on_ground:
            self.body.vel_x *= 0.8
        self.body.move_and_collide(dt, self.room.solids, self.room.one_ways)

    def _think(self, dt: float, player) -> None:
        self.body.vel_x = 0.0

    def _start_attack(self) -> None:
        self.state = "windup"
        self.state_timer = self.attack["windup_ms"] / 1000.0

    def draw(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        r = self.body.rect
        if self.state == "dead" and self.dead_timer <= 0:
            return
        if self.anim:
            self.anim.draw(surface, r.topleft, self.facing)
            if self.hit_flash > 0:
                pygame.draw.rect(surface, c["dummy_flash"], r.inflate(2, 2), 1)
        else:
            color = self.body_color()
            if self.hit_flash > 0:
                color = c["dummy_flash"]
            pygame.draw.rect(surface, color, r)
            eye_x = r.right - 6 if self.facing > 0 else r.left + 3
            pygame.draw.rect(surface, c["player_eye"], (eye_x, r.y + 8, 3, 3))

        if self.state == "windup":
            w, h = self.attack.get("hitbox", [26, 24])
            x = r.right if self.facing > 0 else r.left - w
            pygame.draw.rect(
                surface, c["ember"], (x, r.centery - h // 2, w, h), 1
            )

        if self.health.hp < self.health.max_hp and self.health.alive:
            bar_w = 24
            pygame.draw.rect(surface, c["bg"], (r.centerx - bar_w // 2, r.y - 6, bar_w, 3))
            filled = int(bar_w * self.health.hp / self.health.max_hp)
            pygame.draw.rect(
                surface, c["ember"], (r.centerx - bar_w // 2, r.y - 6, filled, 3)
            )

    def body_color(self) -> tuple[int, int, int]:
        return (140, 90, 80)


class ChaserEnemy(Enemy):
    def _think(self, dt: float, player) -> None:
        if not player.health.alive:
            return
        dx = player.rect.centerx - self.rect.centerx
        adx = abs(dx)
        if adx > self.data.get("detect_range", 150):
            return
        self.facing = 1 if dx > 0 else -1
        if adx <= self.attack.get("range", 28) and self.cooldown <= 0:
            self._start_attack()
            return
        speed = self.data["speed"] * self.status.speed_multiplier()
        self.body.vel_x = self.facing * speed


class ShooterEnemy(Enemy):
    def _think(self, dt: float, player) -> None:
        if not player.health.alive:
            return
        dx = player.rect.centerx - self.rect.centerx
        adx = abs(dx)
        if adx > self.data.get("detect_range", 210):
            return
        self.facing = 1 if dx > 0 else -1
        keep = self.data.get("keep_distance", 90)
        speed = self.data["speed"] * self.status.speed_multiplier()
        if adx < keep - 20:
            self.body.vel_x = -self.facing * speed
        elif adx > keep + 30:
            self.body.vel_x = self.facing * speed
        if adx <= self.data.get("detect_range", 210) and self.cooldown <= 0:
            self._start_attack()

    def _advance_attack(self, dt: float) -> None:
        was_windup = self.state == "windup"
        super()._advance_attack(dt)
        if was_windup and self.state == "active":
            self.pending_projectile = self.attack.get("projectile")

    def body_color(self) -> tuple[int, int, int]:
        return (150, 140, 160)