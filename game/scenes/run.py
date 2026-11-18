import random
from types import SimpleNamespace

import pygame

from game import config
from game.core.animation import build_clips
from game.core.assets import load_json
from game.core.scene_manager import Scene
from game.entities.enemy import ChaserEnemy, ShooterEnemy
from game.entities.pickup import EMBER_VALUE, FIRE_SEED, POTION, POTION_HEAL, Pickup
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.combat import TEAM_ENEMY, TEAM_PLAYER, CombatSystem
from game.systems.loot import load_tables, roll_table
from game.systems.weapons import scaling_bonus, weapon_damage, weapon_level

WEAPON_LABELS = {
    "worn_flame_blade": "Worn Flame Blade",
    "ash_daggers": "Ash Daggers",
    "bell_hammer": "Bell Hammer",
    "rift_spear": "Rift Spear",
    "desperate_edge": "Desperate Edge",
    "gale_daggers": "Gale Daggers",
    "ember_staff": "Ember Staff",
}


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
            hazards=[
                SimpleNamespace(
                    kind="spikes", rect=pygame.Rect(200, 238, 40, 8), damage=15
                ),
                SimpleNamespace(
                    kind="poison", rect=pygame.Rect(136, 240, 48, 6), damage=4.0
                ),
            ],
        )
        weapon_data = load_json("game/data/weapons.json")["weapons"]
        self.weapon_slots = [
            self._make_weapon(weapon_data["worn_flame_blade"], "worn_flame_blade", 2),
            self._make_weapon(weapon_data["desperate_edge"], "desperate_edge", 1),
            self._make_weapon(weapon_data["gale_daggers"], "gale_daggers", 1),
        ]
        self.weapon_index = 0
        self.weapon = self.weapon_slots[0]
        self.skills = load_json("game/data/skills.json")["skills"]
        self.skill_cooldowns = {skill_id: 0.0 for skill_id in self.skills}
        self.cast_id = 0
        self.enemy_data = load_json("game/data/enemies.json")["enemies"]
        self.loot_tables = load_tables(load_json("game/data/loot_tables.json"))
        anim_data = load_json("game/data/animations.json")
        self.player_anims = build_clips(anim_data["player"])
        self.enemy_anims = {
            enemy_id: build_clips(section)
            for enemy_id, section in anim_data["enemies"].items()
        }
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
        self.skill_fx: list[list] = []
        self._font = None
        self._font_small = None

    def enter(self) -> None:
        self._font = pygame.font.Font(None, 14)
        self._font_small = pygame.font.Font(None, 11)
        self._reset_arena()

    @staticmethod
    def _make_weapon(data: dict, weapon_id: str, level: int) -> dict:
        weapon = dict(data)
        weapon["id"] = weapon_id
        weapon["level"] = level
        return weapon

    def _reset_arena(self) -> None:
        self.combat = CombatSystem(self.rng)
        self.weapon = self.weapon_slots[self.weapon_index]
        self.player = Player(48, 200, self.weapon, self.player_anims)
        self.combat.register(self.player)
        self.enemies = [
            ChaserEnemy(
                "ash_crawler",
                300,
                200,
                self.enemy_data["ash_crawler"],
                self.room,
                self.enemy_anims["ash_crawler"],
            ),
            ShooterEnemy(
                "bone_archer",
                430,
                200,
                self.enemy_data["bone_archer"],
                self.room,
                self.enemy_anims["bone_archer"],
            ),
        ]
        for enemy in self.enemies:
            self.combat.register(enemy)
        self.projectiles = []
        self.pickups = []
        self.skill_cooldowns = {skill_id: 0.0 for skill_id in self.skills}
        self.cast_id = 0
        self.skill_fx = []
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
        if inp.is_action_just_pressed("swap") and self.player.attack_phase is None:
            self.weapon_index = (self.weapon_index + 1) % len(self.weapon_slots)
            self.weapon = self.weapon_slots[self.weapon_index]
            self.player.weapon = self.weapon
        self._update_hazards()
        self._update_skills(inp, dt)
        for fx in self.skill_fx:
            fx[1] -= dt
        self.skill_fx = [fx for fx in self.skill_fx if fx[1] > 0]

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

    def _update_hazards(self) -> None:
        player = self.player
        for hazard in self.room.hazards:
            if not hazard.rect.colliderect(player.rect):
                continue
            if hazard.kind == "spikes":
                player.take_hit(hazard.damage, hazard.rect.center, 120.0)
            elif hazard.kind == "poison":
                player.status.apply("poison", 2.0, hazard.damage, max_stacks=1)

    def _update_skills(self, inp, dt: float) -> None:
        for skill_id in self.skill_cooldowns:
            self.skill_cooldowns[skill_id] = max(
                0.0, self.skill_cooldowns[skill_id] - dt
            )
        skill = self.skills.get("ember_burst")
        if not skill or not inp.is_action_just_pressed("skill1"):
            return
        if self.skill_cooldowns["ember_burst"] > 0:
            return
        if not self.player.mana.spend(skill["mana_cost"]):
            return
        self.skill_cooldowns["ember_burst"] = skill["cooldown"]
        self.player.cast_timer = 0.25
        self.cast_id += 1
        radius = skill["radius"]
        cx, cy = self.player.rect.center
        area = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        hits = self.combat.resolve_melee(
            f"skill:ember_burst:{self.cast_id}",
            area,
            TEAM_PLAYER,
            skill["damage"],
            skill.get("knockback", 0.0),
            source_pos=(cx, cy),
        )
        for target, _, _ in hits:
            for effect in skill.get("effects", []):
                if effect.get("status"):
                    target.status.apply(
                        effect["status"],
                        effect.get("duration", 1.0),
                        effect.get("potency", 0.0),
                        effect.get("max_stacks", 1),
                    )
        self.skill_fx.append([area, 0.2])
        if hits:
            self.hitstop = config.HITSTOP_ON_HIT

    def draw(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        surface.fill(c["bg"])
        for rect in self.room.solids:
            pygame.draw.rect(surface, c["terrain"], rect)
            pygame.draw.rect(surface, c["terrain_top"], (rect.x, rect.y, rect.w, 2))
        for rect in self.room.one_ways:
            pygame.draw.rect(surface, c["one_way"], rect)
        for hazard in self.room.hazards:
            if hazard.kind == "spikes":
                r = hazard.rect
                for x in range(r.x, r.right, 8):
                    pygame.draw.polygon(
                        surface,
                        c["spike"],
                        [(x, r.bottom), (x + 4, r.top), (x + 8, r.bottom)],
                    )
            else:
                pygame.draw.rect(surface, c["poison"], hazard.rect)

        for pickup in self.pickups:
            pickup.draw(surface)
        for projectile in self.projectiles:
            projectile.draw(surface)
        for enemy in self.enemies:
            enemy.draw(surface)
        for rect, _ttl in self.skill_fx:
            pygame.draw.rect(surface, c["slash"], rect, 2)
        self.player.draw(surface)
        self._draw_hud(surface)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        p = self.player
        bars = (
            (p.health.hp / p.health.max_hp, c["ember"]),
            (p.stamina.value / p.stamina.max_value, c["stamina"]),
            (p.mana.value / p.mana.max_value, c["mana"]),
        )
        for i, (ratio, color) in enumerate(bars):
            y = 12 + i * 8
            pygame.draw.rect(surface, c["terrain"], (12, y, 64, 5))
            pygame.draw.rect(surface, color, (12, y, int(64 * ratio), 5))
        skill_cd = self.skill_cooldowns.get("ember_burst", 0.0)
        info = (
            f"HP {p.health.hp}/{p.health.max_hp}  ST {int(p.stamina.value)}  "
            f"MP {int(p.mana.value)}  U "
            + ("READY" if skill_cd <= 0 else f"{skill_cd:.1f}s")
        )
        surface.blit(self._font.render(info, True, c["hud"]), (12, 36))
        weapon = self.weapon
        bonus = scaling_bonus(weapon, p)
        weapon_line = (
            f"{WEAPON_LABELS.get(weapon.get('id'), '?')} "
            f"Lv{weapon_level(weapon)}  DMG {weapon_damage(weapon, p):.1f}"
            + (f" (+{int(bonus * 100)}%)" if bonus > 0 else "")
        )
        weapon_text = self._font.render(weapon_line, True, c["hud"])
        surface.blit(weapon_text, (468 - weapon_text.get_width(), 12))
        held = ", ".join(sorted(self.game.input.pressed_actions())) or "-"
        status = (
            "K "
            + ("READY" if p.parry_cooldown <= 0 else f"{p.parry_cooldown:.2f}s")
            + f"   embers {self.embers}   kills {self.kills}   held: {held}"
        )
        surface.blit(self._font_small.render(status, True, c["hud_dim"]), (12, 50))
        hint = (
            "A/D move  SPACE jump  SHIFT dash  J attack  K parry  "
            "Q swap  U skill  R reset  ESC quit"
        )
        surface.blit(self._font_small.render(hint, True, c["hud_dim"]), (12, 258))