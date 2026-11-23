import pygame

from game import config
from game.components.health import Health
from game.components.physics import PhysicsBody
from game.components.resources import ResourcePool
from game.components.status_effects import StatusEffects
from game.core.animation import Animator
from game.systems.combat import TEAM_PLAYER
from game.systems.weapons import weapon_damage

DEFAULT_WEAPON = {
    "base_damage": 12,
    "hitbox": [40, 26],
    "windup_ms": 50,
    "active_ms": 80,
    "recovery_ms": 140,
    "knockback": 120,
}

PARRY_WINDOW = 0.15
PARRY_COOLDOWN = 0.5
COUNTER_DURATION = 1.2
COUNTER_MULTIPLIER = 1.5
HURT_IFRAMES = 0.8
WEAPON_ANIM_CLASSES = {"tachi", "longsword", "zhanmadao", "shield", "bow"}


class Player:
    def __init__(
        self,
        x: float,
        y: float,
        weapon: dict | None = None,
        anim_clips: dict | None = None,
    ) -> None:
        self.body = PhysicsBody(x, y, *config.PLAYER_SIZE)
        self.team = TEAM_PLAYER
        self.weapon = weapon or DEFAULT_WEAPON
        self.anim = Animator(anim_clips) if anim_clips else None
        self.health = Health(100)
        self.stamina = ResourcePool(
            config.STAMINA_MAX, config.STAMINA_REGEN, config.STAMINA_REGEN_DELAY
        )
        self.mana = ResourcePool(
            config.MANA_MAX, config.MANA_REGEN, config.MANA_REGEN_DELAY
        )
        self.status = StatusEffects()
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
        self.hurt_timer = 0.0
        self.parry_timer = 0.0
        self.parry_cooldown = 0.0
        self.counter_timer = 0.0
        self.cast_timer = 0.0
        self.attack_phase: str | None = None
        self.attack_timer = 0.0
        self.attack_hit = False
        self.pending_shot = False
        self.attack_power = 0.0
        self.swing_id = 0
        self.death_reported = False
        self._fall_speed = 0.0
        self._dot_pool = 0.0
        self.ghosts: list[list] = []

    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect

    @property
    def attack_hitbox(self) -> pygame.Rect | None:
        if self.attack_phase != "active" or self.weapon.get("projectile"):
            return None
        w, h = self.weapon["hitbox"]
        r = self.body.rect
        x = r.right if self.facing > 0 else r.left - w
        return pygame.Rect(x, r.centery - h // 2, w, h)

    @property
    def is_parrying(self) -> bool:
        return self.parry_timer > 0

    def on_hit(self, amount: int, source_pos, knockback: float) -> None:
        self.take_hit(amount, source_pos, knockback)

    def take_hit(self, amount: int, source_pos, knockback: float) -> bool:
        if not self.health.alive or self.invuln > 0:
            return False
        remaining = int(self.status.absorb(amount))
        if remaining > 0:
            self.health.take_damage(remaining)
        self.invuln = HURT_IFRAMES
        self.hurt_timer = 0.25
        if knockback and self.health.alive:
            direction = -1 if source_pos and source_pos[0] > self.rect.centerx else 1
            self.body.vel_x = direction * knockback * 0.8
            self.body.vel_y = -120.0
        if not self.health.alive:
            self.state = "dead"
        return True

    def parry_success(self) -> None:
        self.parry_timer = 0.0
        self.counter_timer = COUNTER_DURATION

    def heal(self, amount: int) -> None:
        self.health.heal(amount)

    def _apply_fall_damage(self) -> None:
        if self._fall_speed < config.FALL_SAFE_SPEED:
            return
        damage = int(
            round((self._fall_speed - config.FALL_SAFE_SPEED) * config.FALL_DAMAGE_SCALE)
        )
        if damage <= 0:
            return
        self.health.take_damage(damage)
        self.hurt_timer = 0.2
        if not self.health.alive:
            self.state = "dead"

    def update(self, dt: float, inp, room) -> None:
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.attack_buffer = max(0.0, self.attack_buffer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.drop_timer = max(0.0, self.drop_timer - dt)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.parry_timer = max(0.0, self.parry_timer - dt)
        self.parry_cooldown = max(0.0, self.parry_cooldown - dt)
        self.counter_timer = max(0.0, self.counter_timer - dt)
        self.cast_timer = max(0.0, self.cast_timer - dt)
        self.stamina.update(dt)
        self.mana.update(dt)
        if not self.body.on_ground:
            self.coyote = max(0.0, self.coyote - dt)

        dot = self.status.update(dt)
        if dot > 0:
            self._dot_pool += self.status.absorb(dot)
            whole = int(self._dot_pool)
            if whole > 0:
                self._dot_pool -= whole
                self.health.take_damage(whole)
                if not self.health.alive:
                    self.state = "dead"

        if not self.health.alive:
            self.state = "dead"
            self.body.vel_x = 0.0
            self.body.vel_y = min(
                self.body.vel_y + config.GRAVITY * dt, config.MAX_FALL
            )
            self.body.move_and_collide(dt, room.solids, room.one_ways)
            if self.anim:
                self.anim.play("death")
                self.anim.update(dt)
            return

        stunned = self.status.stunned
        was_airborne = not self.body.on_ground
        if was_airborne:
            self._fall_speed = max(self._fall_speed, self.body.vel_y)
        axis = 0.0 if stunned else inp.get_axis("move_x")
        if axis != 0:
            self.facing = 1 if axis > 0 else -1
        if not stunned:
            if inp.is_action_just_pressed("jump"):
                self.jump_buffer = config.JUMP_BUFFER
            if inp.is_action_just_pressed("attack"):
                self.attack_buffer = config.ATTACK_BUFFER
            if (
                inp.is_action_just_pressed("offhand")
                and self.parry_cooldown <= 0
                and self.dash_time <= 0
                and self.weapon.get("parry_scale", 1.0) > 0
            ):
                if self.stamina.spend(config.PARRY_STAMINA_COST):
                    self.parry_timer = PARRY_WINDOW * self.weapon.get(
                        "parry_scale", 1.0
                    )
                    self.parry_cooldown = PARRY_COOLDOWN
            if (
                inp.is_action_just_pressed("dash")
                and self.dash_cooldown <= 0
                and self.dash_time <= 0
            ):
                if self.stamina.spend(config.DASH_STAMINA_COST):
                    self.dash_time = config.DASH_TIME
                    self.dash_cooldown = config.DASH_COOLDOWN
                    self.invuln = max(self.invuln, config.DASH_INVULN)
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
            target = axis * config.MOVE_SPEED * self.status.speed_multiplier()
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
                and not stunned
                and inp.is_action_pressed("down")
                and self.body.on_ground
                and self.body.ground_is_one_way
            ):
                self.drop_timer = config.DROP_THROUGH_TIME
                self.jump_buffer = 0.0
                self.body.on_ground = False
            elif (
                self.jump_buffer > 0
                and not stunned
                and (self.body.on_ground or self.coyote > 0)
            ):
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

        if self.body.on_ground:
            if was_airborne:
                self._apply_fall_damage()
            self._fall_speed = 0.0

        if not stunned:
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

        if self.anim:
            self.anim.play(self._animation_name())
            self.anim.update(dt)

    def _attack_animation_name(self) -> str:
        weapon_class = self.weapon.get("class", "longsword")
        if weapon_class not in WEAPON_ANIM_CLASSES:
            weapon_class = "longsword"
        return f"attack_{weapon_class}_{self.attack_phase}"

    def _animation_name(self) -> str:
        if not self.health.alive:
            return "death"
        if self.hurt_timer > 0:
            return "hurt"
        if self.dash_time > 0:
            return "dash"
        if self.cast_timer > 0:
            return "skill"
        if self.attack_phase:
            return self._attack_animation_name()
        if self.parry_timer > 0:
            return "parry"
        if not self.body.on_ground:
            return "jump" if self.body.vel_y < 0 else "fall"
        if abs(self.body.vel_x) > 5:
            return "run"
        return "idle"

    def _update_attack(self, dt: float) -> None:
        if self.attack_phase is None:
            if self.attack_buffer > 0 and self.dash_time <= 0:
                self.attack_phase = "windup"
                self.attack_timer = self.weapon["windup_ms"] / 1000.0
                self.attack_buffer = 0.0
                self.attack_hit = False
                self.swing_id += 1
                self.attack_power = weapon_damage(self.weapon, self)
                if self.counter_timer > 0:
                    self.attack_power *= self.weapon.get(
                        "counter_multiplier", COUNTER_MULTIPLIER
                    )
                    self.counter_timer = 0.0
            return
        self.attack_timer -= dt
        if self.attack_timer > 0:
            return
        if self.attack_phase == "windup":
            self.attack_phase = "active"
            self.attack_timer = self.weapon["active_ms"] / 1000.0
            if self.weapon.get("projectile"):
                self.pending_shot = True
        elif self.attack_phase == "active":
            self.attack_phase = "recovery"
            self.attack_timer = self.weapon["recovery_ms"] / 1000.0
        else:
            self.attack_phase = None

    def draw(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        for rect, ttl in self.ghosts:
            ghost = pygame.Surface(rect.size, pygame.SRCALPHA)
            ghost.fill((*c["ember"], int(120 * ttl / 0.2)))
            surface.blit(ghost, rect.topleft)

        if self.invuln > 0 and self.hurt_timer <= 0 and int(self.invuln * 20) % 2 == 0:
            return
        r = self.body.rect
        if self.anim:
            self.anim.draw(surface, r.topleft, self.facing)
        else:
            body_color = c["dummy_flash"] if self.hurt_timer > 0 else c["player"]
            pygame.draw.rect(surface, body_color, r)
            pygame.draw.rect(surface, c["ember"], (r.x, r.y + 6, r.w, 3))
            eye_x = r.right - 5 if self.facing > 0 else r.left + 2
            pygame.draw.rect(surface, c["player_eye"], (eye_x, r.y + 10, 3, 3))

        if self.counter_timer > 0:
            pygame.draw.rect(surface, c["slash"], r.inflate(4, 4), 1)
        if self.is_parrying:
            arc_x = r.right + 2 if self.facing > 0 else r.left - 6
            pygame.draw.rect(surface, c["slash"], (arc_x, r.centery - 8, 4, 16))

        hitbox = self.attack_hitbox
        if config.DEBUG_HITBOXES and hitbox:
            pygame.draw.rect(surface, c["slash"], hitbox, 1)
        elif self.attack_phase == "windup" and not self.anim:
            spark_x = r.right if self.facing > 0 else r.left - 4
            pygame.draw.rect(surface, c["ember"], (spark_x, r.centery - 2, 4, 4))