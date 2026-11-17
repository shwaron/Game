import pygame

from game import config
from game.components.physics import PhysicsBody


class Player:
    def __init__(self, x: float, y: float) -> None:
        self.body = PhysicsBody(x, y, *config.PLAYER_SIZE)
        self.facing = 1
        self.state = "fall"
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.attack_buffer = 0.0
        self.dash_cooldown = 0.0
        self.dash_time = 0.0
        self.dash_dir = 1
        self.invuln = 0.0
        self.drop_timer = 0.0
        self.attack_phase: str | None = None
        self.attack_timer = 0.0
        self.attack_hit = False
        self.ghosts: list[list] = []

    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect

    @property
    def attack_hitbox(self) -> pygame.Rect | None:
        if self.attack_phase != "active":
            return None
        w, h = config.ATTACK_HITBOX
        r = self.body.rect
        x = r.right if self.facing > 0 else r.left - w
        return pygame.Rect(x, r.centery - h // 2, w, h)

    def update(self, dt: float, inp, room) -> None:
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.attack_buffer = max(0.0, self.attack_buffer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.drop_timer = max(0.0, self.drop_timer - dt)
        if not self.body.on_ground:
            self.coyote = max(0.0, self.coyote - dt)

        axis = inp.get_axis("move_x")
        if axis != 0:
            self.facing = 1 if axis > 0 else -1
        if inp.is_action_just_pressed("jump"):
            self.jump_buffer = config.JUMP_BUFFER
        if inp.is_action_just_pressed("attack"):
            self.attack_buffer = config.ATTACK_BUFFER
        if (
            inp.is_action_just_pressed("dash")
            and self.dash_cooldown <= 0
            and self.dash_time <= 0
        ):
            self.dash_time = config.DASH_TIME
            self.dash_cooldown = config.DASH_COOLDOWN
            self.invuln = config.DASH_INVULN
            self.dash_dir = self.facing
            self.body.vel_y = 0.0

        if self.dash_time > 0:
            self.dash_time -= dt
            self.body.vel_x = self.dash_dir * config.DASH_SPEED
            self.body.vel_y = 0.0
            self.body.move_and_collide(dt, room.solids, room.one_ways)
            self.ghosts.append([self.body.rect.copy(), 0.2])
            if self.dash_time <= 0:
                self.body.vel_x = self.facing * config.MOVE_SPEED * 0.6
        else:
            target = axis * config.MOVE_SPEED
            if self.attack_phase and self.body.on_ground:
                target *= 0.3
            accel = config.GROUND_ACCEL if self.body.on_ground else config.AIR_ACCEL
            if axis == 0 and self.body.on_ground:
                accel = config.GROUND_DECEL
            if self.body.vel_x < target:
                self.body.vel_x = min(target, self.body.vel_x + accel * dt)
            else:
                self.body.vel_x = max(target, self.body.vel_x - accel * dt)

            self.body.vel_y = min(
                self.body.vel_y + config.GRAVITY * dt, config.MAX_FALL
            )

            if (
                self.jump_buffer > 0
                and inp.is_action_pressed("down")
                and self.body.on_ground
                and self.body.ground_is_one_way
            ):
                self.drop_timer = config.DROP_THROUGH_TIME
                self.jump_buffer = 0.0
                self.body.on_ground = False
            elif self.jump_buffer > 0 and (self.body.on_ground or self.coyote > 0):
                self.body.vel_y = config.JUMP_VELOCITY
                self.jump_buffer = 0.0
                self.coyote = 0.0
                self.body.on_ground = False

            if (
                not inp.is_action_pressed("jump")
                and self.body.vel_y < config.JUMP_CUT_VELOCITY
            ):
                self.body.vel_y = config.JUMP_CUT_VELOCITY

            self.body.move_and_collide(
                dt, room.solids, room.one_ways, drop_through=self.drop_timer > 0
            )
            if self.body.on_ground:
                self.coyote = config.COYOTE_TIME

        self._update_attack(dt)

        for ghost in self.ghosts:
            ghost[1] -= dt
        self.ghosts = [g for g in self.ghosts if g[1] > 0]

        if self.dash_time > 0:
            self.state = "dash"
        elif self.attack_phase:
            self.state = "attack"
        elif not self.body.on_ground:
            self.state = "jump" if self.body.vel_y < 0 else "fall"
        elif abs(self.body.vel_x) > 5:
            self.state = "run"
        else:
            self.state = "idle"

    def _update_attack(self, dt: float) -> None:
        if self.attack_phase is None:
            if self.attack_buffer > 0 and self.dash_time <= 0:
                self.attack_phase = "windup"
                self.attack_timer = config.ATTACK_WINDUP
                self.attack_buffer = 0.0
                self.attack_hit = False
            return
        self.attack_timer -= dt
        if self.attack_timer > 0:
            return
        if self.attack_phase == "windup":
            self.attack_phase = "active"
            self.attack_timer = config.ATTACK_ACTIVE
        elif self.attack_phase == "active":
            self.attack_phase = "recovery"
            self.attack_timer = config.ATTACK_RECOVERY
        else:
            self.attack_phase = None

    def draw(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        for rect, ttl in self.ghosts:
            ghost = pygame.Surface(rect.size, pygame.SRCALPHA)
            ghost.fill((*c["ember"], int(120 * ttl / 0.2)))
            surface.blit(ghost, rect.topleft)

        if self.invuln > 0 and int(self.invuln * 20) % 2 == 0:
            return
        r = self.body.rect
        pygame.draw.rect(surface, c["player"], r)
        pygame.draw.rect(surface, c["ember"], (r.x, r.y + 6, r.w, 3))
        eye_x = r.right - 5 if self.facing > 0 else r.left + 2
        pygame.draw.rect(surface, c["player_eye"], (eye_x, r.y + 10, 3, 3))

        hitbox = self.attack_hitbox
        if hitbox:
            pygame.draw.rect(surface, c["slash"], hitbox)
        elif self.attack_phase == "windup":
            spark_x = r.right if self.facing > 0 else r.left - 4
            pygame.draw.rect(surface, c["ember"], (spark_x, r.centery - 2, 4, 4))