import random
from types import SimpleNamespace

import pygame

from game import config
from game.core.assets import load_json
from game.core.scene_manager import Scene
from game.entities.enemy import ChaserEnemy, ShooterEnemy
from game.entities.pickup import EMBER_VALUE, FIRE_SEED, POTION, POTION_HEAL, Pickup
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.combat import TEAM_ENEMY, TEAM_PLAYER, CombatSystem
from game.systems.loot import load_tables, roll_table


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
        self.weapon = load_json("game/data/weapons.json")["weapons"][
            "worn_flame_blade"
        ]
        self.enemy_data = load_json("game/data/enemies.json")["enemies"]
        self.loot_tables = load_tables(load_json("game/data/loot_tables.json"))
        self.rng = random.Random()
        self.combat = CombatSystem(self.rng)
        self.player = None
        self.enemies: list = []
        self.projectiles: list = []
        self.pickups: list = []
        self.embers = 0
        self.kills = 0
        self.hitstop = 0.0
        self.respawn_timer = 0.0
        self.death_timer = 0.0
        self._font = None
        self._font_small = None

    def enter(self) -> None:
        self._font = pygame.font.Font(None, 14)
        self._font_small = pygame.font.Font(None, 11)
        self._reset_arena()

    def _reset_arena(self) -> None:
        self.combat = CombatSystem(self.rng)
        self.player = Player(48, 200, self.weapon)
        self.combat.register(self.player)
        self.enemies = [
            ChaserEnemy(
                "ash_crawler", 300, 200, self.enemy_data["ash_crawler"], self.room
            ),
            ShooterEnemy(
                "bone_archer", 430, 200, self.enemy_data["bone_archer"], self.room
            ),
        ]
        for enemy in self.enemies:
            self.combat.register(enemy)
        self.projectiles = []
        self.pickups = []
        self.respawn_timer = 0.0
        self.death_timer = 0.0

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._reset_arena()

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.is_action_just_pressed("pause"):
            self.game.quit()
            return
        if self.hitstop > 0:
            self.hitstop -= dt
            return

        if not self.player.health.alive:
            self.death_timer += dt
            if not self.player.death_reported:
                self.player.death_reported = True
                self.game.bus.publish(
                    "player.died",
                    {"run_id": 0, "depth": 1, "cause": "combat"},
                )
            self.player.update(dt, inp, self.room)
            if self.death_timer > 1.2:
                self._reset_arena()
            return

        self.player.update(dt, inp, self.room)

        hitbox = self.player.attack_hitbox
        if hitbox:
            hits = self.combat.resolve_melee(
                f"player:{self.player.swing_id}",
                hitbox,
                TEAM_PLAYER,
                self.player.attack_power,
                self.player.weapon.get("knockback", 0.0),
                source_pos=(self.player.rect.centerx, self.player.rect.centery),
                crit_chance=0.05,
            )
            if hits:
                self.hitstop = config.HITSTOP_ON_HIT

        for enemy in list(self.enemies):
            enemy.update(dt, self.player)
            if enemy.health.alive:
                enemy_hitbox = enemy.attack_hitbox
                if enemy_hitbox:
                    if self.player.is_parrying and enemy_hitbox.colliderect(
                        self.player.rect
                    ):
                        self.player.parry_success()
                        enemy.stagger(0.4)
                        self.hitstop = 0.08
                    else:
                        hits = self.combat.resolve_melee(
                            f"enemy:{id(enemy)}:{enemy.swing_id}",
                            enemy_hitbox,
                            TEAM_ENEMY,
                            enemy.data["damage"],
                            enemy.attack.get("knockback", 0.0),
                            source_pos=(
                                enemy.rect.centerx,
                                enemy.rect.centery,
                            ),
                        )
                        if hits:
                            self.hitstop = config.HITSTOP_ON_HIT
                if enemy.pending_projectile:
                    self._spawn_projectile(enemy)
                    enemy.pending_projectile = None
            else:
                if not enemy.death_reported:
                    enemy.death_reported = True
                    self.kills += 1
                    self.game.bus.publish(
                        "enemy.killed",
                        {
                            "enemy_id": enemy.enemy_id,
                            "position": (
                                enemy.rect.centerx,
                                enemy.rect.centery,
                            ),
                            "loot_table": enemy.data.get("loot_table", ""),
                        },
                    )
                    self._drop_loot(enemy)
                if enemy.dead_timer <= 0:
                    self.combat.unregister(enemy)
                    self.enemies.remove(enemy)

        for projectile in list(self.projectiles):
            projectile.update(dt, self.room)
            if projectile.dead:
                self.projectiles.remove(projectile)
                continue
            if projectile.team == TEAM_ENEMY and projectile.rect.colliderect(
                self.player.rect
            ):
                if self.player.is_parrying:
                    projectile.reflect()
                    self.player.parry_success()
                    self.hitstop = 0.08
                    continue
            hits = self.combat.resolve_melee(
                f"projectile:{id(projectile)}",
                projectile.rect,
                projectile.team,
                projectile.damage,
                80.0,
                source_pos=(projectile.x, projectile.y),
            )
            if hits:
                self.hitstop = config.HITSTOP_ON_HIT
                self.projectiles.remove(projectile)

        for pickup in list(self.pickups):
            pickup.update(dt, self.room)
            if pickup.collect_rect.colliderect(self.player.rect):
                self.pickups.remove(pickup)
                self._collect(pickup)

        if not self.enemies:
            self.respawn_timer += dt
            if self.respawn_timer > 3.0:
                self._reset_arena()

    def _spawn_projectile(self, enemy) -> None:
        spec = enemy.pending_projectile
        speed = spec.get("speed", 160)
        size = tuple(spec.get("size", [6, 3]))
        self.projectiles.append(
            Projectile(
                enemy.rect.centerx,
                enemy.rect.centery,
                enemy.facing * speed,
                0.0,
                enemy.data["damage"],
                TEAM_ENEMY,
                size,
                spec.get("life", 3.0),
            )
        )

    def _drop_loot(self, enemy) -> None:
        table = self.loot_tables.get(enemy.data.get("loot_table", ""))
        if not table:
            return
        item_id = roll_table(table, self.rng)
        self.pickups.append(
            Pickup(item_id, enemy.rect.centerx, enemy.rect.centery)
        )

    def _collect(self, pickup) -> None:
        if pickup.item_id == FIRE_SEED:
            self.embers += EMBER_VALUE
        elif pickup.item_id == POTION:
            self.player.heal(POTION_HEAL)
        self.game.bus.publish(
            "loot.picked",
            {"item_id": pickup.item_id, "rarity": "common", "slot": "none"},
        )

    def draw(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        surface.fill(c["bg"])
        for rect in self.room.solids:
            pygame.draw.rect(surface, c["terrain"], rect)
            pygame.draw.rect(surface, c["terrain_top"], (rect.x, rect.y, rect.w, 2))
        for rect in self.room.one_ways:
            pygame.draw.rect(surface, c["one_way"], rect)

        for pickup in self.pickups:
            pickup.draw(surface)
        for projectile in self.projectiles:
            projectile.draw(surface)
        for enemy in self.enemies:
            enemy.draw(surface)
        self.player.draw(surface)
        self._draw_hud(surface)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        p = self.player
        pygame.draw.rect(surface, c["terrain"], (12, 12, 64, 6))
        filled = int(64 * p.health.hp / p.health.max_hp)
        pygame.draw.rect(surface, c["ember"], (12, 12, filled, 6))
        info = (
            f"HP {p.health.hp}/{p.health.max_hp}   embers {self.embers}   "
            f"kills {self.kills}   parry "
            + ("READY" if p.parry_cooldown <= 0 else f"{p.parry_cooldown:.2f}s")
        )
        surface.blit(self._font.render(info, True, c["hud"]), (12, 24))
        held = ", ".join(sorted(self.game.input.pressed_actions())) or "-"
        surface.blit(
            self._font_small.render(f"held: {held}", True, c["hud_dim"]), (12, 40)
        )
        hint = (
            "A/D move  SPACE jump  SHIFT dash  J attack  K parry  R reset  ESC quit"
        )
        surface.blit(self._font_small.render(hint, True, c["hud_dim"]), (12, 258))