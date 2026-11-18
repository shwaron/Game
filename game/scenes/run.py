import math
import random

import pygame

from game import config
from game.core.animation import build_clips
from game.core.assets import load_json
from game.core.camera import Camera
from game.core.scene_manager import Scene
from game.entities.enemy import ChaserEnemy, ShooterEnemy
from game.entities.pickup import (
    EMBER_VALUE,
    FIRE_SEED,
    MANUAL,
    POTION,
    POTION_HEAL,
    Pickup,
)
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.scenes.bamboo_world import (
    FLOOR_Y,
    HEIGHT,
    HUD_GOLD,
    LANTERN_GOLD,
    START_ROOM,
    WIDTH,
    WOOD,
    WOOD_DARK,
    WOOD_EDGE,
    build_world,
    load_cjk_font,
)
from game.systems.combat import TEAM_ENEMY, TEAM_PLAYER, CombatSystem
from game.systems.loot import load_tables, roll_table
from game.systems.weapons import scaling_bonus, weapon_damage, weapon_level

TRANSITION_TIME = 0.16
ROOM_TITLE_TIME = 2.8
HINT_TIME = 14.0
ANCHOR_RANGE = 46
ANCHOR_TOAST_TIME = 2.4


class RunScene(Scene):
    def __init__(self, game) -> None:
        self.game = game
        self.loc = load_json("game/data/localization/zh_CN.json")
        self.rooms = build_world()
        weapon_data = load_json("game/data/weapons.json")["weapons"]
        self.weapon_slots = [
            self._make_weapon(weapon_data["worn_flame_blade"], "worn_flame_blade", 2),
            self._make_weapon(weapon_data["desperate_edge"], "desperate_edge", 1),
            self._make_weapon(weapon_data["bell_hammer"], "bell_hammer", 1),
            self._make_weapon(weapon_data["rift_spear"], "rift_spear", 1),
            self._make_weapon(weapon_data["gale_daggers"], "gale_daggers", 1),
            self._make_weapon(weapon_data["ember_staff"], "ember_staff", 1),
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
        self.camera = Camera(WIDTH, HEIGHT)
        self.room = self.rooms[START_ROOM]
        self.world_surface = pygame.Surface((self.room.width, HEIGHT))
        self.combat = CombatSystem(self.rng)
        self.player = None
        self.enemies: list = []
        self.projectiles: list = []
        self.pickups: list = []
        self._loot_sources: dict[int, tuple[str, int]] = {}
        self.embers = 0
        self.kills = 0
        self.hitstop = 0.0
        self.death_timer = 0.0
        self.room_title_timer = 0.0
        self.clear_banner_timer = 0.0
        self.hint_timer = 0.0
        self.exit_cooldown = 0.0
        self.transition: dict | None = None
        self.show_map = False
        self.discovered: set[str] = set()
        self.cleared: set[str] = set()
        self.taken_loot: set[tuple[str, int]] = set()
        self.lit_anchors: set[str] = set()
        self.opened_chests: set[tuple[str, int]] = set()
        self.map_targets: list = []
        self.map_selection = 0
        self.toast_timer = 0.0
        self.toast_text = ""
        self.manual_choice: bool = False
        self.manual_selection = 0
        self.manual_stats = {"attack": 0, "hp": 0, "armor": 0}
        self.anchor_glow = pygame.Surface((44, 44))
        self.anchor_glow.fill((0, 0, 0))
        for radius in range(20, 3, -2):
            strength = 21 - radius
            pygame.draw.circle(
                self.anchor_glow,
                (strength, int(strength * 0.62), int(strength * 0.28)),
                (22, 22),
                radius,
            )
        self.skill_fx: list[list] = []
        self.font_title = None
        self.font_info = None
        self.font_tiny = None

    def enter(self) -> None:
        self.font_title = load_cjk_font(15)
        self.font_info = load_cjk_font(10)
        self.font_tiny = load_cjk_font(10)
        self._start_run()

    @staticmethod
    def _make_weapon(data: dict, weapon_id: str, level: int) -> dict:
        weapon = dict(data)
        weapon["id"] = weapon_id
        weapon["level"] = level
        return weapon

    # -- run / room lifecycle -------------------------------------------
    def _start_run(self) -> None:
        for slot in self.weapon_slots:
            slot["level"] = 2 if slot["id"] == "worn_flame_blade" else 1
        self.weapon_index = 0
        self.weapon = self.weapon_slots[0]
        self.player = Player(0, 0, self.weapon, self.player_anims)
        self.enemies = []
        self.projectiles = []
        self.pickups = []
        self._loot_sources = {}
        self.embers = 0
        self.kills = 0
        self.hitstop = 0.0
        self.death_timer = 0.0
        self.clear_banner_timer = 0.0
        self.hint_timer = HINT_TIME
        self.exit_cooldown = 0.0
        self.transition = None
        self.show_map = False
        self.discovered = set()
        self.cleared = set()
        self.taken_loot = set()
        self.lit_anchors = {START_ROOM}
        self.opened_chests = set()
        self.map_targets = []
        self.map_selection = 0
        self.toast_timer = 0.0
        self.toast_text = ""
        self.manual_choice = False
        self.manual_selection = 0
        self.manual_stats = {"attack": 0, "hp": 0, "armor": 0}
        self.skill_cooldowns = {skill_id: 0.0 for skill_id in self.skills}
        self.cast_id = 0
        self.skill_fx = []
        self._enter_room(START_ROOM, "start")

    def _enter_room(self, room_id: str, entry: str) -> None:
        room = self.rooms[room_id]
        spawn = room.entries[entry]
        self.room = room
        self.player.body.x = float(spawn[0])
        self.player.body.y = float(spawn[1])
        self.player.body.vel_x = 0.0
        self.player.body.vel_y = 0.0
        self.player.body.on_ground = False
        self.player.drop_timer = 0.0
        self.player.dash_time = 0.0
        self.player.cast_timer = 0.0
        self.player.parry_timer = 0.0
        self.player.attack_phase = None
        self.player.attack_timer = 0.0
        self.player.jump_buffer = 0.0
        self.player.attack_buffer = 0.0
        self.player.hurt_timer = 0.0
        self.player.invuln = max(self.player.invuln, 0.25)
        self.player.ghosts = []
        self.player.plunging = False
        self.player.plunge_landed = False
        self.player._fall_apex = None
        if entry == "anchor":
            self.player.facing = 1
        else:
            self.player.facing = 1 if spawn[0] < room.width / 2 else -1
        self.player.state = "fall"

        self.combat = CombatSystem(self.rng)
        self.combat.register(self.player)
        self.enemies = []
        if room.room_id not in self.cleared:
            self.enemies = [self._spawn_enemy(spawn) for spawn in room.spawns]
            for enemy in self.enemies:
                self.combat.register(enemy)
        self.projectiles = []
        self.pickups = []
        self._loot_sources = {}
        for index, (item_id, x, y) in enumerate(room.loot):
            source = (room.room_id, index)
            if source in self.taken_loot:
                continue
            pickup = Pickup(item_id, x, y)
            self.pickups.append(pickup)
            self._loot_sources[id(pickup)] = source
        self.world_surface = pygame.Surface((room.width, HEIGHT))
        self.camera.snap(self.player.rect, room.width, HEIGHT)
        self.room_title_timer = ROOM_TITLE_TIME
        self.clear_banner_timer = 0.0
        self.exit_cooldown = 0.55
        self.discovered.add(room.room_id)

    def _spawn_enemy(self, spawn: dict):
        enemy_id = spawn["enemy_id"]
        data = self.enemy_data[enemy_id]
        enemy_type = ShooterEnemy if data.get("keep_distance") else ChaserEnemy
        return enemy_type(
            enemy_id,
            spawn["x"],
            spawn["y"],
            data,
            self.room,
            self.enemy_anims[enemy_id],
        )

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._start_run()

    # -- update ---------------------------------------------------------
    def update(self, dt: float) -> None:
        inp = self.game.input

        self.room.art.update(dt)
        self.room_title_timer = max(0.0, self.room_title_timer - dt)
        self.clear_banner_timer = max(0.0, self.clear_banner_timer - dt)
        self.hint_timer = max(0.0, self.hint_timer - dt)
        self.toast_timer = max(0.0, self.toast_timer - dt)
        self.exit_cooldown = max(0.0, self.exit_cooldown - dt)

        if self.transition is not None:
            self._update_transition(dt)
            return

        if self.manual_choice:
            self._update_manual_choice(inp)
            return

        if inp.is_action_just_pressed("map") and self.player.health.alive:
            self.show_map = not self.show_map
            if self.show_map:
                self._refresh_map_targets()
            return
        if self.show_map:
            if inp.is_action_just_pressed("pause"):
                self.show_map = False
                return
            if inp.is_action_just_pressed("move_left"):
                self._cycle_map_anchor(-1)
            elif inp.is_action_just_pressed("move_right"):
                self._cycle_map_anchor(1)
            if inp.is_action_just_pressed("interact") and self.map_targets:
                self._begin_teleport(self.map_targets[self.map_selection])
            return

        if inp.is_action_just_pressed("pause"):
            self.game.quit()
            return

        if self.hitstop > 0:
            self.hitstop -= dt
            return

        self.player.update(dt, inp, self.room)
        if not self.player.health.alive:
            self.death_timer += dt
            if not self.player.death_reported:
                self.player.death_reported = True
                self.game.bus.publish(
                    "player.died",
                    {"run_id": 0, "depth": 1, "cause": "combat"},
                )
            if self.death_timer > 1.6:
                self._start_run()
            return

        if inp.is_action_just_pressed("interact"):
            if self._interact_chest():
                return
            if self._interact_anchor():
                return

        self.camera.update(
            dt, self.player.rect, self.room.width, HEIGHT, self.player.facing
        )

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

        if self.player.plunge_landed:
            self._resolve_plunge_kill()

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

        if (
            not self.enemies
            and self.room.spawns
            and self.room.room_id not in self.cleared
        ):
            self.cleared.add(self.room.room_id)
            self.clear_banner_timer = 2.4

        if self.exit_cooldown <= 0 and self.player.health.alive:
            for exit_ in self.room.exits:
                if self.player.rect.colliderect(exit_.rect):
                    self._begin_transition(exit_)
                    break

    def _update_transition(self, dt: float) -> None:
        self.transition["timer"] -= dt
        if self.transition["timer"] > 0:
            return
        if self.transition["phase"] == "out":
            target = self.transition["target"]
            entry = self.transition["entry"]
            self._enter_room(target, entry)
            self.transition = {"phase": "in", "timer": TRANSITION_TIME}
        else:
            self.transition = None

    def _begin_transition(self, exit_) -> None:
        self.transition = {
            "phase": "out",
            "timer": TRANSITION_TIME,
            "target": exit_.target,
            "entry": exit_.entry,
        }
        self.exit_cooldown = 0.9

    def _near_anchor(self):
        if not self.player.health.alive:
            return None
        px = self.player.rect.centerx
        feet = self.player.rect.bottom
        for anchor in self.room.anchors:
            if (
                abs(px - anchor.x) <= ANCHOR_RANGE
                and abs(feet - FLOOR_Y) <= 14
            ):
                return anchor
        return None

    def _interact_anchor(self) -> bool:
        anchor = self._near_anchor()
        if anchor is None:
            return False
        if anchor.room_id not in self.lit_anchors:
            self.lit_anchors.add(anchor.room_id)
            self._show_toast(self.loc.get("ui.anchor.toast", "灯锚已亮 · 舆图可传送"))
            self.game.bus.publish("anchor.lit", {"room": anchor.room_id})
            return False
        self.show_map = True
        self._refresh_map_targets()
        return True

    def _show_toast(self, text: str) -> None:
        self.toast_text = text
        self.toast_timer = ANCHOR_TOAST_TIME

    def _near_chest(self):
        if not self.player.health.alive:
            return None
        px = self.player.rect.centerx
        feet = self.player.rect.bottom
        for chest in self.room.chests:
            if (chest.room_id, chest.x) in self.opened_chests:
                continue
            if (
                abs(px - chest.rect.centerx) <= 28
                and abs(feet - chest.rect.bottom) <= 22
            ):
                return chest
        return None

    def _interact_chest(self) -> bool:
        chest = self._near_chest()
        if chest is None:
            return False
        self.opened_chests.add((chest.room_id, chest.x))
        weapon = next(
            (slot for slot in self.weapon_slots if slot["id"] == chest.weapon_id),
            None,
        )
        name_key = f"weapon.{chest.weapon_id}.name"
        name = self.loc.get(name_key, chest.weapon_id)
        upgraded = False
        level = 0
        if weapon is not None:
            level = int(weapon.get("level", 1))
            max_level = int(weapon.get("max_level", 5))
            if level < max_level:
                level += 1
                weapon["level"] = level
                upgraded = True
        self.embers += chest.embers
        if upgraded:
            text = self.loc.get(
                "ui.chest.toast_upgrade",
                "宝箱：{weapon} 升至 {level} 级 · 余烬 +{embers}",
            ).format(weapon=name, level=level, embers=chest.embers)
        else:
            text = self.loc.get(
                "ui.chest.toast_max", "宝箱：{weapon} 已至顶级 · 余烬 +{embers}"
            ).format(weapon=name, embers=chest.embers)
        self._show_toast(text)
        self.game.bus.publish(
            "chest.opened",
            {"room": chest.room_id, "weapon": chest.weapon_id, "level": level},
        )
        return True

    def _resolve_plunge_kill(self) -> None:
        hitbox = self.player.plunge_hitbox
        if hitbox is None:
            return
        killed = False
        for enemy in self.enemies:
            if enemy.health.alive and hitbox.colliderect(enemy.rect):
                enemy.health.take_damage(enemy.health.hp + 1)
                killed = True
        if killed:
            self.skill_fx.append([hitbox.inflate(16, 10), 0.2])
            self.hitstop = 0.09

    # -- manuals ---------------------------------------------------------
    def _manual_options(self) -> list[tuple[str, str, str]]:
        return [
            (
                "attack",
                self.loc.get("ui.manual.attack.name", "残页 · 破锋"),
                self.loc.get("ui.manual.attack.desc", "攻击 +2"),
            ),
            (
                "hp",
                self.loc.get("ui.manual.hp.name", "残页 · 固元"),
                self.loc.get("ui.manual.hp.desc", "气血上限 +10"),
            ),
            (
                "armor",
                self.loc.get("ui.manual.armor.name", "残页 · 铁衣"),
                self.loc.get("ui.manual.armor.desc", "护甲 +1"),
            ),
        ]

    def _update_manual_choice(self, inp) -> None:
        options = self._manual_options()
        if inp.is_action_just_pressed("move_left"):
            self.manual_selection = (self.manual_selection - 1) % len(options)
        elif inp.is_action_just_pressed("move_right"):
            self.manual_selection = (self.manual_selection + 1) % len(options)
        elif inp.is_action_just_pressed("interact"):
            self._apply_manual_choice(options[self.manual_selection][0])

    def _apply_manual_choice(self, stat: str) -> None:
        if stat == "attack":
            self.player.bonus_attack += 2
            self.manual_stats["attack"] += 2
        elif stat == "hp":
            self.player.health.max_hp += 10
            self.player.health.heal(10)
            self.manual_stats["hp"] += 10
        elif stat == "armor":
            self.player.health.armor += 1
            self.manual_stats["armor"] += 1
        self.manual_choice = False
        self.manual_selection = 0
        self._show_toast(self.loc.get("ui.manual.gained", "秘籍已参悟"))
        self.game.bus.publish("manual.learned", {"stat": stat})

    def _refresh_map_targets(self) -> None:
        current = self.room.room_id
        ordered = sorted(
            self.rooms.values(), key=lambda room: (room.map_pos[0], room.map_pos[1])
        )
        self.map_targets = [
            anchor
            for room in ordered
            if room.room_id != current and room.room_id in self.lit_anchors
            for anchor in room.anchors
        ]
        if self.map_selection >= len(self.map_targets):
            self.map_selection = 0

    def _cycle_map_anchor(self, step: int) -> None:
        if not self.map_targets:
            return
        self.map_selection = (self.map_selection + step) % len(self.map_targets)

    def _begin_teleport(self, anchor) -> None:
        self.show_map = False
        self.transition = {
            "phase": "out",
            "timer": TRANSITION_TIME,
            "target": anchor.room_id,
            "entry": anchor.entry,
        }
        self.exit_cooldown = 0.9

    def _spawn_projectile(self, enemy) -> None:
        spec = enemy.pending_projectile
        speed = spec.get("speed", 160)
        size = tuple(spec.get("size", [6, 2]))
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
        self.pickups.append(Pickup(item_id, enemy.rect.centerx, enemy.rect.centery))

    def _collect(self, pickup) -> None:
        if pickup.item_id == FIRE_SEED:
            self.embers += EMBER_VALUE
        elif pickup.item_id == POTION:
            self.player.heal(POTION_HEAL)
        elif pickup.item_id == MANUAL:
            self.manual_choice = True
            self.manual_selection = 0
        source = self._loot_sources.pop(id(pickup), None)
        if source is not None:
            self.taken_loot.add(source)
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

    # -- draw -----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        world = self.world_surface
        self.room.art.draw_back(world)
        self._draw_exit_markers(world)
        self._draw_anchors(world)
        self._draw_chests(world)
        self._draw_hazards(world)
        for pickup in self.pickups:
            pickup.draw(world)
        for projectile in self.projectiles:
            projectile.draw(world)
        for enemy in self.enemies:
            enemy.draw(world)
        for rect, ttl in self.skill_fx:
            radius = max(2, int(rect.w / 2 * (1.0 - ttl / 0.2)))
            pygame.draw.circle(world, (255, 176, 88), rect.center, radius, 2)
            pygame.draw.circle(
                world, (255, 220, 150), rect.center, max(1, radius - 5), 1
            )
        self.player.draw(world)

        surface.blit(world, (0, 0), self.camera.rect)
        self.room.art.draw_front(surface)
        self._draw_anchor_prompt(surface)
        self._draw_chest_prompt(surface)
        self._draw_exit_hints(surface)
        self._draw_enemy_names(surface)
        self._draw_hud(surface)
        self._draw_room_title(surface)
        self._draw_toast(surface)
        self._draw_clear_banner(surface)
        if self.manual_choice:
            self._draw_manual_choice(surface)
        if self.show_map:
            self._draw_minimap(surface)
        if not self.player.health.alive:
            self._draw_death(surface)
        self._draw_fade(surface)

    def _draw_exit_markers(self, surface: pygame.Surface) -> None:
        cx = self.player.rect.centerx
        for exit_ in self.room.exits:
            rect = exit_.rect
            near = abs(cx - rect.centerx) < 90
            if exit_.kind == "hatch":
                pygame.draw.rect(
                    surface, WOOD_EDGE, (rect.x, FLOOR_Y - 2, rect.w, 8)
                )
                pygame.draw.rect(
                    surface, WOOD_DARK, (rect.x + 2, FLOOR_Y - 1, rect.w - 4, 5)
                )
                pygame.draw.rect(
                    surface, (8, 8, 7), (rect.x + 6, FLOOR_Y + 1, rect.w - 12, 10)
                )
                for hx in range(rect.x + 8, rect.right - 6, 8):
                    pygame.draw.line(
                        surface,
                        WOOD,
                        (hx, FLOOR_Y - 1),
                        (hx + 3, FLOOR_Y + 3),
                        1,
                    )
                pygame.draw.line(
                    surface,
                    LANTERN_GOLD,
                    (rect.centerx - 3, FLOOR_Y + 7),
                    (rect.centerx + 3, FLOOR_Y + 7),
                    1,
                )
            elif exit_.kind == "stairs":
                pygame.draw.rect(
                    surface, (14, 12, 10), (rect.x + 4, rect.y + 8, rect.w - 8, rect.h - 8)
                )
                pygame.draw.rect(
                    surface, WOOD_EDGE, (rect.x + 2, rect.y + 6, rect.w - 4, 52), 1
                )
                pygame.draw.line(
                    surface,
                    LANTERN_GOLD if near else (120, 96, 60),
                    (rect.centerx, rect.bottom - 4),
                    (rect.centerx, rect.y + 12),
                    1,
                )
            else:
                color = LANTERN_GOLD if near else (132, 104, 66)
                pygame.draw.rect(
                    surface,
                    color,
                    (rect.x if rect.centerx < WIDTH else rect.right - 2, rect.y + 14, 2, 58),
                )
                pygame.draw.polygon(
                    surface,
                    color,
                    [
                        (rect.centerx - 3, rect.y + 26),
                        (rect.centerx + 3, rect.y + 26),
                        (rect.centerx, rect.y + 32),
                    ],
                )

    def _draw_anchors(self, surface: pygame.Surface) -> None:
        t = self.room.art.time
        for anchor in self.room.anchors:
            x = anchor.x
            lit = anchor.room_id in self.lit_anchors
            if lit:
                surface.blit(
                    self.anchor_glow,
                    (x - 22, 192),
                    special_flags=pygame.BLEND_RGB_ADD,
                )
            pygame.draw.rect(surface, (46, 43, 36), (x - 8, 241, 16, 5))
            pygame.draw.rect(surface, (94, 88, 70), (x - 8, 240, 16, 2))
            pygame.draw.rect(surface, (58, 55, 46), (x - 3, 224, 6, 17))
            pygame.draw.rect(surface, (108, 100, 78), (x - 2, 225, 2, 15))
            pygame.draw.rect(surface, (72, 67, 54), (x - 10, 219, 20, 5))
            pygame.draw.rect(surface, (130, 120, 90), (x - 9, 218, 18, 2))
            if lit:
                sway = int(round(math.sin(t * 5.0 + anchor.x * 0.05) * 1.5))
                pygame.draw.polygon(
                    surface,
                    (236, 112, 48),
                    [(x, 206), (x - 4, 214), (x, 219), (x + 4, 214)],
                )
                pygame.draw.polygon(
                    surface,
                    (255, 170, 84),
                    [(x, 209), (x - 2, 214), (x, 218), (x + 2, 214)],
                )
                pygame.draw.polygon(
                    surface,
                    (255, 226, 154),
                    [(x, 212), (x - 1, 215), (x, 217), (x + 1, 215)],
                )
                pygame.draw.circle(surface, (255, 238, 190), (x + sway, 207), 1)
            else:
                pygame.draw.line(surface, (78, 86, 82), (x, 210), (x, 214), 1)
                pygame.draw.circle(surface, (72, 82, 80), (x, 216), 2)
                pygame.draw.circle(surface, (38, 45, 45), (x, 216), 1)
                pygame.draw.line(surface, (86, 104, 104), (x - 3, 221), (x + 3, 221), 1)

    def _draw_chests(self, surface: pygame.Surface) -> None:
        t = self.room.art.time
        for chest in self.room.chests:
            r = chest.rect
            opened = (chest.room_id, chest.x) in self.opened_chests
            pygame.draw.rect(surface, (44, 30, 20), (r.x - 1, r.bottom - 2, r.w + 2, 3))
            if opened:
                pygame.draw.rect(surface, (58, 42, 28), (r.x, r.y + 6, r.w, r.h - 6))
                pygame.draw.rect(surface, (30, 22, 16), (r.x + 2, r.y + 4, r.w - 4, 5))
                pygame.draw.rect(surface, (150, 120, 74), (r.x + 1, r.y + 1, r.w - 2, 3))
                pygame.draw.rect(surface, (92, 70, 44), (r.x + 2, r.y + 8, r.w - 4, 1))
            else:
                surface.blit(
                    self.anchor_glow,
                    (r.centerx - 22, r.y - 16),
                    special_flags=pygame.BLEND_RGB_ADD,
                )
                pygame.draw.rect(surface, (104, 70, 38), r)
                pygame.draw.rect(surface, (138, 98, 54), (r.x + 1, r.y + 4, r.w - 2, r.h - 5))
                pygame.draw.rect(surface, (196, 160, 96), (r.x + 1, r.y + 3, r.w - 2, 2))
                pygame.draw.rect(surface, (56, 38, 22), r, 1)
                pygame.draw.rect(surface, (120, 88, 50), (r.x, r.y + 6, r.w, 1))
                pygame.draw.rect(
                    surface, (232, 194, 112), (r.centerx - 1, r.y + 7, 3, 4)
                )
                sx = r.centerx + int(round(math.sin(t * 2.4 + chest.x) * 10))
                sy = r.y - 6 + int(round(math.sin(t * 3.1 + chest.x) * 2))
                pygame.draw.line(surface, (255, 226, 150), (sx - 1, sy), (sx + 1, sy))
                pygame.draw.line(surface, (255, 226, 150), (sx, sy - 1), (sx, sy + 1))

    def _blit_prompt(
        self, surface: pygame.Surface, text: str, sx: int, sy: int
    ) -> None:
        label = self.font_tiny.render(text, True, (232, 214, 174))
        plate = pygame.Surface(
            (label.get_width() + 8, label.get_height() + 4), pygame.SRCALPHA
        )
        plate.fill((8, 7, 6, 170))
        lx = max(6, min(WIDTH - label.get_width() - 14, sx - label.get_width() // 2))
        ly = max(18, min(HEIGHT - 26, sy))
        surface.blit(plate, (lx - 4, ly - 2))
        surface.blit(label, (lx, ly))

    def _draw_anchor_prompt(self, surface: pygame.Surface) -> None:
        if (
            self.transition is not None
            or not self.player.health.alive
            or self.show_map
            or self.manual_choice
        ):
            return
        anchor = self._near_anchor()
        if anchor is None:
            return
        lit = anchor.room_id in self.lit_anchors
        key = "ui.anchor.open" if lit else "ui.anchor.light"
        fallback = "E 舆图传送" if lit else "E 点亮灯锚"
        sx = anchor.x - round(self.camera.x)
        sy = 206 - round(self.camera.y) - self.font_tiny.get_height() - 14
        self._blit_prompt(surface, self.loc.get(key, fallback), sx, sy)

    def _draw_chest_prompt(self, surface: pygame.Surface) -> None:
        if (
            self.transition is not None
            or not self.player.health.alive
            or self.show_map
            or self.manual_choice
        ):
            return
        chest = self._near_chest()
        if chest is None:
            return
        sx = chest.rect.centerx - round(self.camera.x)
        sy = chest.rect.y - round(self.camera.y) - self.font_tiny.get_height() - 8
        self._blit_prompt(
            surface, self.loc.get("ui.chest.prompt", "E 开启宝箱"), sx, sy
        )

    def _draw_toast(self, surface: pygame.Surface) -> None:
        if self.toast_timer <= 0 or self.show_map:
            return
        alpha = min(255, int(255 * self.toast_timer / 0.6))
        text = self.toast_text or self.loc.get("ui.anchor.toast", "灯锚已亮 · 舆图可传送")
        label = self.font_info.render(text, True, (238, 214, 160))
        plate = pygame.Surface((label.get_width() + 16, 15), pygame.SRCALPHA)
        plate.fill((8, 7, 6, 170))
        pygame.draw.line(plate, (150, 116, 68), (4, 0), (plate.get_width() - 4, 0), 1)
        plate.blit(label, (8, 0))
        plate.set_alpha(alpha)
        surface.blit(plate, ((WIDTH - plate.get_width()) // 2, 146))

    def _draw_manual_choice(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 5, 4, 200))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(74, 44, WIDTH - 148, 176)
        pygame.draw.rect(surface, (12, 11, 9), panel)
        pygame.draw.rect(surface, (150, 116, 68), panel, 1)
        title = self.loc.get("ui.manual.title", "拾得秘籍残页")
        subtitle = self.loc.get("ui.manual.subtitle", "参悟一页 · 择一而修")
        title_surf = self.font_title.render(title, True, (238, 214, 160))
        sub_surf = self.font_tiny.render(subtitle, True, (166, 158, 138))
        surface.blit(title_surf, (panel.centerx - title_surf.get_width() // 2, 52))
        surface.blit(sub_surf, (panel.centerx - sub_surf.get_width() // 2, 70))
        options = self._manual_options()
        for index, (_, name, desc) in enumerate(options):
            row = pygame.Rect(panel.x + 14, 88 + index * 30, panel.w - 28, 26)
            selected = index == self.manual_selection
            pygame.draw.rect(
                surface, (26, 22, 16) if selected else (18, 16, 13), row
            )
            pygame.draw.rect(
                surface,
                (226, 190, 118) if selected else (66, 56, 44),
                row,
                1,
            )
            name_surf = self.font_info.render(
                name, True, (246, 224, 172) if selected else (196, 184, 154)
            )
            desc_surf = self.font_tiny.render(
                desc, True, (206, 190, 152) if selected else (148, 138, 118)
            )
            surface.blit(name_surf, (row.x + 8, row.y + 2))
            surface.blit(
                desc_surf,
                (row.right - desc_surf.get_width() - 8, row.y + 7),
            )
        hint = self.loc.get("ui.manual.hint", "A/D 选择 · E 参悟")
        hint_surf = self.font_tiny.render(hint, True, (166, 158, 138))
        surface.blit(
            hint_surf, (panel.centerx - hint_surf.get_width() // 2, panel.bottom - 20)
        )

    def _draw_exit_hints(self, surface: pygame.Surface) -> None:
        if self.transition is not None or not self.player.health.alive:
            return
        px = self.player.rect.centerx
        for exit_ in self.room.exits:
            sx = exit_.rect.centerx - round(self.camera.x)
            if sx < -60 or sx > WIDTH + 60:
                continue
            sy = exit_.rect.centery - round(self.camera.y)
            near = abs(px - exit_.rect.centerx) < 104
            color = (226, 196, 134) if near else (148, 120, 84)
            pygame.draw.polygon(
                surface,
                color,
                [(sx - 3, sy - 3), (sx + 3, sy - 3), (sx, sy + 2)],
            )
            if not near:
                continue
            label = self.loc.get(exit_.label_key, exit_.target)
            if exit_.hidden:
                label = self.loc.get("ui.exit.secret", "暗门") + " · " + label
            text = self.font_tiny.render(label, True, (232, 214, 174))
            plate = pygame.Surface(
                (text.get_width() + 8, text.get_height() + 4), pygame.SRCALPHA
            )
            plate.fill((8, 7, 6, 170))
            lx = max(6, min(WIDTH - text.get_width() - 14, sx - text.get_width() // 2))
            ly = max(18, min(HEIGHT - 26, sy - text.get_height() - 12))
            surface.blit(plate, (lx - 4, ly - 2))
            surface.blit(text, (lx, ly))

    def _draw_hazards(self, surface: pygame.Surface) -> None:
        for hazard in self.room.hazards:
            r = hazard.rect
            if hazard.kind == "spikes":
                pygame.draw.rect(surface, (48, 34, 25), (r.x, r.bottom - 3, r.w, 3))
                for x in range(r.x + 2, r.right, 8):
                    pygame.draw.polygon(
                        surface,
                        (164, 160, 148),
                        [(x, r.bottom), (x + 2, r.top), (x + 4, r.bottom)],
                    )
                    pygame.draw.line(
                        surface,
                        (220, 214, 196),
                        (x + 2, r.top),
                        (x + 3, r.bottom - 1),
                        1,
                    )
            else:
                pygame.draw.ellipse(surface, (66, 78, 42), r.inflate(8, 2))
                pygame.draw.ellipse(surface, (98, 114, 54), r)
                for dx in (4, 15, 26):
                    if r.x + dx < r.right:
                        pygame.draw.circle(
                            surface, (142, 150, 78), (r.x + dx, r.y + 3), 1
                        )

    def _draw_enemy_names(self, surface: pygame.Surface) -> None:
        cam_x = self.camera.x
        cam_y = self.camera.y
        for enemy in self.enemies:
            if not enemy.health.alive:
                continue
            if enemy.health.hp >= enemy.health.max_hp:
                continue
            key = enemy.data.get("name_key", f"enemy.{enemy.enemy_id}.name")
            name = self.loc.get(key, enemy.enemy_id)
            label = self.font_tiny.render(name, True, (232, 214, 174))
            shadow = self.font_tiny.render(name, True, (14, 12, 10))
            r = enemy.rect
            x = r.centerx - label.get_width() // 2 - round(cam_x)
            y = r.y - 20 - round(cam_y)
            if x < -label.get_width() or x > WIDTH:
                continue
            surface.blit(shadow, (x + 1, y + 1))
            surface.blit(label, (x, y))

    def _bestiary_text(self) -> str:
        if self.room.room_id in self.cleared:
            return self.loc.get("ui.hud.cleared_room", "此间已清")
        if not self.room.spawns:
            return self.loc.get("ui.hud.peaceful", "此间暂无妖物")
        names = []
        for spawn in self.room.spawns:
            data = self.enemy_data.get(spawn["enemy_id"], {})
            key = data.get("name_key", f"enemy.{spawn['enemy_id']}.name")
            name = self.loc.get(key, spawn["enemy_id"])
            if name not in names:
                names.append(name)
        return self.loc.get("ui.hud.bestiary_prefix", "妖物：") + " · ".join(names)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        c = config.COLORS
        p = self.player
        rows = (
            (
                self.loc.get("ui.hud.hp", "气血"),
                f"{p.health.hp}/{p.health.max_hp}",
                p.health.hp / p.health.max_hp,
                c["ember"],
            ),
            (
                self.loc.get("ui.hud.stamina", "体力"),
                f"{int(p.stamina.value)}/{int(p.stamina.max_value)}",
                p.stamina.value / p.stamina.max_value,
                c["stamina"],
            ),
            (
                self.loc.get("ui.hud.mana", "内力"),
                f"{int(p.mana.value)}/{int(p.mana.max_value)}",
                p.mana.value / p.mana.max_value,
                c["mana"],
            ),
        )
        rendered_rows = []
        max_right = 112
        for i, (label, value_text, ratio, color) in enumerate(rows):
            y = 8 + i * 12
            label_surf = self.font_info.render(label, True, (222, 208, 180))
            value_surf = self.font_info.render(value_text, True, (204, 192, 166))
            rendered_rows.append((y, label_surf, value_surf, ratio, color))
            max_right = max(max_right, 108 + value_surf.get_width())

        skill_cd = self.skill_cooldowns.get("ember_burst", 0.0)
        skill_name = self.loc.get("skill.ember_burst.name", "烬爆")
        ready = self.loc.get("ui.hud.ready", "就绪")
        seconds = self.loc.get("ui.hud.seconds", "秒")
        state = ready if skill_cd <= 0 else f"{skill_cd:.1f}{seconds}"
        skill_surf = self.font_info.render(f"{skill_name} {state}", True, HUD_GOLD)
        max_right = max(max_right, 12 + skill_surf.get_width())

        bestiary_surf = self.font_tiny.render(self._bestiary_text(), True, HUD_GOLD)
        max_right = max(max_right, 12 + bestiary_surf.get_width())

        panel = pygame.Surface((max_right - 2, 74), pygame.SRCALPHA)
        panel.fill((8, 7, 6, 178))
        surface.blit(panel, (6, 4))

        for y, label_surf, value_surf, ratio, color in rendered_rows:
            surface.blit(label_surf, (12, y - 1))
            pygame.draw.rect(surface, (18, 16, 16), (38, y + 3, 64, 5))
            pygame.draw.rect(surface, color, (38, y + 3, int(64 * ratio), 5))
            pygame.draw.rect(surface, (50, 42, 36), (38, y + 3, 64, 5), 1)
            surface.blit(value_surf, (108, y - 1))

        surface.blit(skill_surf, (12, 44))
        surface.blit(bestiary_surf, (12, 58))

        weapon = self.weapon
        bonus = scaling_bonus(weapon, p)
        name_key = weapon.get("name_key", f"weapon.{weapon.get('id')}.name")
        weapon_name = self.loc.get(name_key, weapon.get("id", "?"))
        weapon_line = (
            f"{self.weapon_index + 1}/{len(self.weapon_slots)} "
            f"{weapon_name} 等级{weapon_level(weapon)} "
            f"{self.loc.get('ui.hud.damage', '伤害')} {weapon_damage(weapon, p):.1f}"
            + (f" +{int(bonus * 100)}%" if bonus > 0 else "")
        )
        loot_line = f"余烬 {self.embers}   击杀 {self.kills}"
        manual_line = ""
        stats = self.manual_stats
        if stats["attack"] or stats["hp"] or stats["armor"]:
            manual_line = (
                f"秘籍 攻+{stats['attack']} 血+{stats['hp']} 御+{stats['armor']}"
            )
        weapon_surf = self.font_tiny.render(weapon_line, True, (220, 210, 184))
        loot_surf = self.font_tiny.render(loot_line, True, (166, 158, 138))
        manual_surf = (
            self.font_tiny.render(manual_line, True, (196, 176, 132))
            if manual_line
            else None
        )
        panel_h = weapon_surf.get_height() + loot_surf.get_height() + 8
        if manual_surf is not None:
            panel_h += manual_surf.get_height()
        weapon_panel = pygame.Surface(
            (
                max(
                    weapon_surf.get_width(),
                    loot_surf.get_width(),
                    manual_surf.get_width() if manual_surf else 0,
                )
                + 10,
                panel_h,
            ),
            pygame.SRCALPHA,
        )
        weapon_panel.fill((8, 7, 6, 178))
        surface.blit(weapon_panel, (472 - weapon_panel.get_width(), 6))
        surface.blit(weapon_surf, (472 - weapon_surf.get_width() - 4, 7))
        line_y = 7 + weapon_surf.get_height() + 2
        surface.blit(loot_surf, (472 - loot_surf.get_width() - 4, line_y))
        if manual_surf is not None:
            surface.blit(
                manual_surf,
                (472 - manual_surf.get_width() - 4, line_y + loot_surf.get_height()),
            )

        if self.hint_timer > 0:
            hint_lines = (
                "A/D 移动  空格 跳  S+空格 跃击  Shift 冲刺  J 攻击  K 弹反",
                "Q 换武器  U 烬爆  E 交互  M 舆图  R 重来  ESC 离开",
            )
            rendered = [
                self.font_tiny.render(line, True, (206, 192, 162))
                for line in hint_lines
            ]
            plate_w = max(line.get_width() for line in rendered) + 8
            plate = pygame.Surface((plate_w, 26), pygame.SRCALPHA)
            plate.fill((8, 7, 6, 168))
            plate.blit(rendered[0], (4, 0))
            plate.blit(rendered[1], (4, 11))
            plate.set_alpha(int(255 * min(1.0, self.hint_timer / 1.2)))
            surface.blit(plate, (10, 240))

    def _draw_room_title(self, surface: pygame.Surface) -> None:
        if self.room_title_timer <= 0:
            return
        alpha = (
            255
            if self.room_title_timer > 0.7
            else int(255 * self.room_title_timer / 0.7)
        )
        title = self.loc.get(self.room.title_key, self.room.room_id)
        subtitle = self.loc.get(self.room.subtitle_key, "")
        text = f"{title} · {subtitle}" if subtitle else title
        label = self.font_info.render(text, True, (238, 214, 160))
        plate = pygame.Surface((label.get_width() + 16, 15), pygame.SRCALPHA)
        plate.fill((8, 7, 6, 160))
        pygame.draw.line(plate, (150, 116, 68), (4, 0), (plate.get_width() - 4, 0), 1)
        plate.blit(label, (8, 0))
        plate.set_alpha(alpha)
        surface.blit(plate, ((WIDTH - plate.get_width()) // 2, 100))

    def _draw_clear_banner(self, surface: pygame.Surface) -> None:
        if self.clear_banner_timer <= 0 or self.show_map:
            return
        alpha = min(255, int(255 * self.clear_banner_timer / 0.6))
        title = self.loc.get("ui.hud.room_cleared", "此处已清")
        label = self.font_title.render(title, True, (238, 214, 160))
        width = label.get_width() + 32
        card = pygame.Surface((width, 22), pygame.SRCALPHA)
        card.fill((8, 7, 6, 170))
        pygame.draw.rect(card, (150, 116, 68), card.get_rect(), 1)
        card.blit(label, ((width - label.get_width()) // 2, 2))
        card.set_alpha(alpha)
        surface.blit(card, ((WIDTH - width) // 2, 124))

    def _map_center(self, pos: tuple[int, int]) -> tuple[int, int]:
        gx, gy = pos
        return 86 + gx * 58, 132 + gy * 44

    def _draw_minimap(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 5, 4, 210))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(24, 22, WIDTH - 48, HEIGHT - 44)
        pygame.draw.rect(surface, (10, 9, 8), panel)
        pygame.draw.rect(surface, (150, 116, 68), panel, 1)
        title = self.loc.get("ui.map.title", "青篁岭 · 竹坞舆图")
        title_surf = self.font_title.render(title, True, (238, 214, 160))
        surface.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 30))
        anchor_total = sum(len(room.anchors) for room in self.rooms.values())
        lit_total = sum(
            1
            for room in self.rooms.values()
            if room.anchors and room.room_id in self.lit_anchors
        )
        subtitle = self.loc.get(
            "ui.map.subtitle", "已探索 {n}/{total} · 灯锚 {a}/{b}"
        ).format(
            n=len(self.discovered),
            total=len(self.rooms),
            a=lit_total,
            b=anchor_total,
        )
        sub_surf = self.font_info.render(subtitle, True, (166, 158, 138))
        surface.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, 48))
        legend = self.loc.get(
            "ui.map.legend", "灯＝传送锚 · 绿＝已清 · 金＝所在"
        )
        legend_surf = self.font_tiny.render(legend, True, (124, 116, 98))
        surface.blit(
            legend_surf, (WIDTH // 2 - legend_surf.get_width() // 2, 66)
        )

        shown: set[str] = set()
        for room_id, room in self.rooms.items():
            if room_id not in self.discovered:
                continue
            for exit_ in room.exits:
                key = tuple(sorted((room_id, exit_.target)))
                if key in shown:
                    continue
                shown.add(key)
                x1, y1 = self._map_center(room.map_pos)
                target = self.rooms[exit_.target]
                x2, y2 = self._map_center(target.map_pos)
                if exit_.target in self.discovered:
                    pygame.draw.line(
                        surface, (110, 96, 68), (x1, y1), (x2, y2), 1
                    )
                else:
                    pygame.draw.line(
                        surface, (62, 56, 46), (x1, y1), (x2, y2), 1
                    )

        unknown: set[str] = set()
        for room_id in self.discovered:
            for exit_ in self.rooms[room_id].exits:
                if exit_.target not in self.discovered:
                    unknown.add(exit_.target)
        for room_id in unknown:
            pos = self._map_center(self.rooms[room_id].map_pos)
            pygame.draw.rect(
                surface, (60, 56, 48), (pos[0] - 8, pos[1] - 5, 16, 10), 1
            )

        selected = (
            self.map_targets[self.map_selection] if self.map_targets else None
        )
        for room_id in self.discovered:
            room = self.rooms[room_id]
            x, y = self._map_center(room.map_pos)
            if room_id == self.room.room_id:
                fill = (255, 224, 156)
                border = (255, 248, 214)
                name_color = (255, 236, 184)
            elif room_id in self.cleared:
                fill = (116, 148, 112)
                border = (152, 180, 146)
                name_color = (152, 180, 146)
            else:
                fill = (146, 126, 94)
                border = (188, 164, 120)
                name_color = (198, 188, 160)
            pygame.draw.rect(surface, fill, (x - 7, y - 4, 14, 8))
            pygame.draw.rect(surface, border, (x - 7, y - 4, 14, 8), 1)
            for anchor in room.anchors:
                self._draw_map_anchor(
                    surface, x + 10, y - 5, room_id in self.lit_anchors
                )
            short_key = f"room.{room_id}.short"
            short_name = self.loc.get(
                short_key, self.loc.get(room.title_key, room_id)
            )
            name = self.font_tiny.render(short_name, True, name_color)
            nx = x - name.get_width() // 2
            ny = y + 6
            pygame.draw.rect(
                surface,
                (10, 9, 8),
                (nx - 2, ny - 1, name.get_width() + 4, name.get_height() + 2),
            )
            surface.blit(name, (nx, ny))

        if selected is not None:
            target_room = self.rooms[selected.room_id]
            tx, ty = self._map_center(target_room.map_pos)
            pygame.draw.polygon(
                surface,
                (255, 232, 174),
                [(tx - 3, ty - 11), (tx + 3, ty - 11), (tx, ty - 7)],
            )
            pygame.draw.rect(
                surface, (255, 240, 200), (tx - 8, ty - 5, 16, 10), 1
            )

        current_name = self.loc.get(self.room.title_key, self.room.room_id)
        current_text = self.loc.get("ui.map.current", "所在 · {name}").format(
            name=current_name
        )
        current_label = self.font_info.render(current_text, True, HUD_GOLD)
        surface.blit(
            current_label, (WIDTH // 2 - current_label.get_width() // 2, 202)
        )

        if selected is not None:
            target_room = self.rooms[selected.room_id]
            target_name = self.loc.get(
                target_room.title_key, target_room.room_id
            )
            travel_text = self.loc.get("ui.map.travel", "E 传送 · {name}").format(
                name=target_name
            )
            travel_color = (242, 212, 150)
        elif self.lit_anchors:
            travel_text = self.loc.get(
                "ui.map.no_target", "此处之外暂无点亮的灯锚"
            )
            travel_color = (166, 158, 138)
        else:
            travel_text = self.loc.get("ui.map.light_hint", "靠近灯锚按 E 点亮")
            travel_color = (166, 158, 138)
        travel_label = self.font_info.render(travel_text, True, travel_color)
        surface.blit(
            travel_label, (WIDTH // 2 - travel_label.get_width() // 2, 216)
        )

        controls = self.loc.get(
            "ui.map.controls", "A/D 选锚 · E 传送 · M 关闭"
        )
        hint_surf = self.font_tiny.render(controls, True, (166, 158, 138))
        surface.blit(
            hint_surf,
            (WIDTH // 2 - hint_surf.get_width() // 2, 232),
        )

    @staticmethod
    def _draw_map_anchor(
        surface: pygame.Surface, cx: int, cy: int, lit: bool
    ) -> None:
        color = (246, 196, 104) if lit else (78, 86, 80)
        pygame.draw.rect(surface, (10, 9, 8), (cx - 2, cy - 4, 5, 7))
        pygame.draw.rect(surface, color, (cx - 2, cy - 4, 5, 7), 1)
        pygame.draw.rect(surface, color, (cx - 1, cy - 2, 3, 3))
        if lit:
            pygame.draw.circle(surface, (255, 232, 174), (cx, cy - 5), 1)

    def _draw_death(self, surface: pygame.Surface) -> None:
        alpha = min(170, int(170 * self.death_timer / 0.6))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 5, 5, alpha))
        surface.blit(overlay, (0, 0))
        if self.death_timer < 0.25:
            return
        title = self.loc.get("ui.death.title", "魂归余烬祠")
        hint = self.loc.get("ui.death.hint", "余烬未熄 · 重头再来")
        title_surf = self.font_title.render(title, True, (238, 214, 160))
        hint_surf = self.font_info.render(hint, True, (188, 172, 138))
        surface.blit(
            title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 112)
        )
        surface.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, 134))

    def _draw_fade(self, surface: pygame.Surface) -> None:
        if self.transition is None:
            return
        timer = max(0.0, self.transition["timer"])
        if self.transition["phase"] == "out":
            alpha = int(255 * (1.0 - timer / TRANSITION_TIME))
        else:
            alpha = int(255 * (timer / TRANSITION_TIME))
        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill((0, 0, 0))
        fade.set_alpha(max(0, min(255, alpha)))
        surface.blit(fade, (0, 0))
