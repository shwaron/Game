"""Room graph, art, and scene transition regression tests."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from game.core.assets import load_json
from game.entities.pickup import FIRE_SEED, MANUAL, POTION
from game.scenes.bamboo_world import HEIGHT, START_ROOM, WIDTH, build_world
from game.scenes.run import TRANSITION_TIME, RunScene

DT = 1 / 60
PLAYER_SIZE = (18, 38)


@pytest.fixture(scope="module")
def world():
    pygame.init()
    return build_world()


@pytest.fixture(scope="module")
def loc():
    return load_json("game/data/localization/zh_CN.json")


@pytest.fixture(scope="module")
def enemy_ids():
    return set(load_json("game/data/enemies.json")["enemies"])


class FakeGame:
    def __init__(self):
        from game.core.event_bus import EventBus
        from game.core.input import InputManager

        self.bus = EventBus()
        self.input = InputManager()

    def quit(self):
        pass


@pytest.fixture(scope="module")
def scene():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    run = RunScene(FakeGame())
    run.enter()
    return run


def test_room_graph_is_connected_and_targets_exist(world):
    assert START_ROOM in world
    assert len(world) >= 8
    seen = {START_ROOM}
    frontier = [START_ROOM]
    while frontier:
        room = world[frontier.pop()]
        for exit_ in room.exits:
            assert exit_.target in world, (room.room_id, exit_.target)
            assert exit_.entry in world[exit_.target].entries
            if exit_.target not in seen:
                seen.add(exit_.target)
                frontier.append(exit_.target)
    assert seen == set(world), set(world) - seen


def test_exits_stay_inside_their_rooms(world):
    for room in world.values():
        assert room.exits, room.room_id
        for exit_ in room.exits:
            rect = exit_.rect
            assert 0 <= rect.x and rect.right <= room.width, room.room_id
            assert 0 <= rect.y and rect.bottom <= HEIGHT, room.room_id


def test_entries_are_clear_of_exits_and_solids(world):
    for room in world.values():
        assert room.entries, room.room_id
        for name, (x, y) in room.entries.items():
            body = pygame.Rect(x, y, *PLAYER_SIZE)
            assert 0 <= x and body.right <= room.width, (room.room_id, name)
            assert 0 <= y and body.bottom <= HEIGHT, (room.room_id, name)
            for exit_ in room.exits:
                assert not body.colliderect(exit_.rect), (
                    room.room_id,
                    name,
                    exit_.target,
                )
            for solid in room.solids:
                assert not body.colliderect(solid), (room.room_id, name)


def test_map_slots_are_unique(world):
    slots = [room.map_pos for room in world.values()]
    assert len(slots) == len(set(slots))


def test_spawns_hazards_and_loot_are_valid(world, enemy_ids):
    for room in world.values():
        for spawn in room.spawns:
            assert spawn["enemy_id"] in enemy_ids, (room.room_id, spawn)
            assert 0 <= spawn["x"] <= room.width, (room.room_id, spawn)
            assert 0 <= spawn["y"] <= HEIGHT - 30, (room.room_id, spawn)
        for hazard in room.hazards:
            assert hazard.kind in {"spikes", "poison"}, room.room_id
            assert hazard.damage > 0
            assert 0 <= hazard.rect.x, room.room_id
            assert hazard.rect.right <= room.width, room.room_id
        for item_id, x, y in room.loot:
            assert item_id in {FIRE_SEED, POTION, MANUAL}, (room.room_id, item_id)
            assert 0 <= x <= room.width, room.room_id
            assert 0 <= y <= HEIGHT, room.room_id


def test_chests_hold_known_weapons_and_stay_inside_rooms(world):
    weapon_ids = set(load_json("game/data/weapons.json")["weapons"])
    chest_rooms = set()
    for room in world.values():
        for chest in room.chests:
            assert chest.room_id == room.room_id
            assert chest.weapon_id in weapon_ids, (room.room_id, chest.weapon_id)
            assert chest.embers > 0
            assert 0 <= chest.rect.x and chest.rect.right <= room.width
            assert 0 <= chest.rect.y and chest.rect.bottom <= 246
            chest_rooms.add(room.room_id)
    assert chest_rooms == {
        "inn_upper",
        "cellar_vault",
        "ridge_fork",
        "valley_gate",
        "temple_gate",
    }


def test_localization_covers_rooms_and_exits(world, loc):
    for room in world.values():
        assert room.title_key in loc, room.room_id
        assert room.subtitle_key in loc, room.room_id
        assert f"room.{room.room_id}.short" in loc, room.room_id
        for exit_ in room.exits:
            assert exit_.label_key in loc, (room.room_id, exit_.label_key)


def test_anchors_are_clear_and_have_entries(world):
    anchors = [
        (room, anchor) for room in world.values() for anchor in room.anchors
    ]
    assert len(anchors) == 7
    assert {anchor.room_id for _, anchor in anchors} == {
        "shrine",
        "inn_front",
        "backyard",
        "cellar_upper",
        "ridge_fork",
        "valley_gate",
        "temple_gate",
    }
    for room, anchor in anchors:
        assert anchor.room_id == room.room_id
        assert 0 < anchor.x < room.width, room.room_id
        assert anchor.entry in room.entries, room.room_id
        assert room.entries[anchor.entry] == (anchor.x - 28, 208)
        body = pygame.Rect(anchor.x - 28, 208, *PLAYER_SIZE)
        approach = pygame.Rect(anchor.x - 44, 200, 88, 46)
        for hazard in room.hazards:
            assert not body.colliderect(hazard.rect), (room.room_id, hazard.kind)
            assert not approach.colliderect(hazard.rect), (
                room.room_id,
                hazard.kind,
                hazard.rect,
            )


def test_every_room_art_draws_headless(world):
    screen = pygame.Surface((WIDTH, HEIGHT))
    for room in world.values():
        world_surface = pygame.Surface((room.width, HEIGHT))
        assert room.art.width == room.width
        room.art.update(DT)
        room.art.draw_back(world_surface)
        room.art.draw_front(screen)


def test_secret_rooms_are_reachable(world):
    assert "cellar_upper" in world and "cellar_vault" in world
    secret_entrances = [
        exit_
        for room in world.values()
        for exit_ in room.exits
        if exit_.hidden and exit_.target.startswith("cellar")
    ]
    assert len(secret_entrances) == 2


def test_all_exits_transition_to_their_target(scene):
    for room_id in list(scene.rooms):
        room = scene.rooms[room_id]
        for exit_ in room.exits:
            scene._enter_room(room_id, next(iter(room.entries)))
            scene.enemies = []
            scene.player.invuln = 5.0
            scene.exit_cooldown = 0.0
            scene.player.body.x = exit_.rect.centerx - scene.player.rect.w / 2
            scene.player.body.y = exit_.rect.centery - scene.player.rect.h / 2
            scene.update(DT)
            assert scene.transition is not None, (room_id, exit_.target)
            assert scene.transition["target"] == exit_.target
            assert scene.transition["entry"] == exit_.entry
            for _ in range(int(TRANSITION_TIME * 2 / DT) + 4):
                scene.update(DT)
                scene.player.invuln = 5.0
            assert scene.transition is None, (room_id, exit_.target)
            assert scene.room.room_id == exit_.target
            spawn = scene.rooms[exit_.target].entries[exit_.entry]
            assert abs(scene.player.body.x - spawn[0]) < 0.01
            assert abs(scene.player.body.y - spawn[1]) < 0.01
            assert 0 <= scene.camera.x <= scene.room.width - WIDTH
            assert exit_.target in scene.discovered


def test_return_entry_does_not_retrigger_exit(scene):
    scene._enter_room("inn_front", "from_cellar")
    scene.player.invuln = 5.0
    for _ in range(90):
        scene.update(DT)
        scene.player.invuln = 5.0
    assert scene.room.room_id == "inn_front"
    assert scene.transition is None


def test_cleared_rooms_stay_empty_in_a_run(scene):
    scene.cleared.add("bamboo_path")
    scene._enter_room("bamboo_path", "start")
    assert scene.enemies == []


def test_vault_loot_is_taken_only_once(scene):
    scene._enter_room("cellar_vault", "west")
    assert len(scene.pickups) == 5
    scene.taken_loot.update(scene._loot_sources.values())
    scene._enter_room("cellar_vault", "west")
    assert scene.pickups == []


def test_minimap_draws(scene):
    scene._enter_room("ridge_fork", "west")
    scene.discovered = set(scene.rooms)
    scene.cleared = {"bamboo_path", "inn_front"}
    scene.lit_anchors = {"shrine", "inn_front", "backyard", "ridge_fork"}
    scene._refresh_map_targets()
    scene.show_map = True
    surface = pygame.Surface((WIDTH, HEIGHT))
    scene.draw(surface)
    scene.show_map = False


def test_anchor_activation_and_map_travel(scene):
    scene._start_run()
    scene._enter_room("inn_front", "west")
    scene.enemies = []
    scene.player.invuln = 5.0
    scene.exit_cooldown = 5.0
    anchor = scene.rooms["inn_front"].anchors[0]
    scene.player.body.x = anchor.x - 28
    scene.player.body.y = 208.0
    scene.player.body.on_ground = True

    inp = scene.game.input
    inp._just = {"interact"}
    inp._pressed = {"interact"}
    scene.update(DT)
    inp._just = set()
    inp._pressed = set()
    assert "inn_front" in scene.lit_anchors
    assert scene.toast_timer > 0

    inp._just = {"interact"}
    inp._pressed = {"interact"}
    scene.update(DT)
    inp._just = set()
    inp._pressed = set()
    assert scene.show_map
    assert scene.map_targets
    assert all(target.room_id != "inn_front" for target in scene.map_targets)
    assert any(target.room_id == START_ROOM for target in scene.map_targets)
    scene.show_map = False

    scene._enter_room("ridge_fork", "west")
    scene.lit_anchors = {
        "shrine",
        "inn_front",
        "backyard",
        "cellar_upper",
        "ridge_fork",
    }
    scene._refresh_map_targets()
    assert all(target.room_id != "ridge_fork" for target in scene.map_targets)
    target = next(
        anchor for anchor in scene.map_targets if anchor.room_id == "backyard"
    )
    scene.map_selection = scene.map_targets.index(target)
    scene._begin_teleport(target)
    assert scene.transition is not None
    assert scene.transition["target"] == "backyard"
    for _ in range(int(TRANSITION_TIME * 2 / DT) + 4):
        scene.update(DT)
        scene.player.invuln = 5.0
    assert scene.transition is None
    assert scene.room.room_id == "backyard"
    spawn = scene.rooms["backyard"].entries[target.entry]
    assert abs(scene.player.body.x - spawn[0]) < 0.01
    assert abs(scene.player.body.y - spawn[1]) < 0.01
    assert "backyard" in scene.lit_anchors
    assert "backyard" in scene.discovered


def test_anchor_state_resets_on_new_run(scene):
    scene.lit_anchors = {"shrine", "inn_front"}
    scene.map_targets = [scene.rooms["inn_front"].anchors[0]]
    scene.map_selection = 1
    scene._start_run()
    assert scene.lit_anchors == {START_ROOM}
    assert scene.map_targets == []
    assert scene.map_selection == 0
    assert scene.toast_timer == 0
    assert scene.opened_chests == set()
    assert scene.manual_stats == {"attack": 0, "hp": 0, "armor": 0}


def test_anchor_visuals_and_toast_draw(scene):
    scene._start_run()
    scene._enter_room("inn_front", "west")
    scene.enemies = []
    scene.player.invuln = 5.0
    anchor = scene.rooms["inn_front"].anchors[0]
    scene.player.body.x = anchor.x - 28
    scene.player.body.y = 208.0
    scene.lit_anchors.add("inn_front")
    scene.toast_timer = 2.0
    surface = pygame.Surface((WIDTH, HEIGHT))
    scene.draw(surface)


def test_chest_opens_once_and_raises_weapon_level(scene):
    scene._start_run()
    scene._enter_room("valley_gate", "west")
    scene.enemies = []
    scene.player.invuln = 5.0
    scene.exit_cooldown = 5.0
    chest = scene.rooms["valley_gate"].chests[0]
    weapon = next(
        slot for slot in scene.weapon_slots if slot["id"] == chest.weapon_id
    )
    base_level = weapon["level"]
    base_embers = scene.embers
    scene.player.body.x = chest.rect.centerx - scene.player.rect.w / 2
    scene.player.body.y = float(chest.rect.bottom - scene.player.rect.h)
    scene.player.body.on_ground = True

    inp = scene.game.input
    inp._just = {"interact"}
    inp._pressed = {"interact"}
    scene.update(DT)
    inp._just = set()
    inp._pressed = set()
    assert (chest.room_id, chest.x) in scene.opened_chests
    assert weapon["level"] == min(base_level + 1, weapon["max_level"])
    assert scene.embers == base_embers + chest.embers
    assert scene.toast_timer > 0
    level_after = weapon["level"]

    scene.draw(pygame.Surface((WIDTH, HEIGHT)))
    scene._enter_room("valley_gate", "west")
    assert (chest.room_id, chest.x) in scene.opened_chests

    inp._just = {"interact"}
    inp._pressed = {"interact"}
    scene.update(DT)
    inp._just = set()
    inp._pressed = set()
    assert weapon["level"] == level_after

    scene._start_run()
    assert scene.opened_chests == set()
    assert scene.weapon_slots[0]["level"] == 2


def test_manual_pickup_opens_choice_and_applies_bonus(scene):
    scene._start_run()
    scene._enter_room("bamboo_path", "start")
    scene.enemies = []
    scene.player.invuln = 5.0
    scene.exit_cooldown = 5.0
    manual = next(p for p in scene.pickups if p.item_id == MANUAL)
    scene._collect(manual)
    scene.pickups.remove(manual)
    assert scene.manual_choice
    scene.draw(pygame.Surface((WIDTH, HEIGHT)))

    inp = scene.game.input
    inp._just = {"move_right"}
    inp._pressed = {"move_right"}
    scene.update(DT)
    inp._just = set()
    inp._pressed = set()
    assert scene.manual_selection == 1

    hp_before = scene.player.health.max_hp
    hp_value = scene.player.health.hp
    inp._just = {"interact"}
    inp._pressed = {"interact"}
    scene.update(DT)
    inp._just = set()
    inp._pressed = set()
    assert not scene.manual_choice
    assert scene.player.health.max_hp == hp_before + 10
    assert scene.player.health.hp == min(hp_before + 10, hp_value + 10)
    assert scene.manual_stats["hp"] == 10
    assert scene.toast_timer > 0

    scene._apply_manual_choice("attack")
    scene._apply_manual_choice("armor")
    assert scene.player.bonus_attack == 2
    assert scene.player.health.armor == 1
    assert scene.manual_stats == {"attack": 2, "hp": 10, "armor": 1}
