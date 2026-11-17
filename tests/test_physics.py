import pygame

from game import config
from game.components.physics import PhysicsBody

DT = config.DT
GROUND = pygame.Rect(0, 246, 480, 24)
PLATFORM = pygame.Rect(120, 190, 96, 8)
WALL = pygame.Rect(200, 0, 8, 270)


def fall(body, solids, one_ways=(), steps=180, drop_through=False):
    for _ in range(steps):
        body.vel_y = min(body.vel_y + config.GRAVITY * DT, config.MAX_FALL)
        body.move_and_collide(DT, solids, list(one_ways), drop_through)
        if body.on_ground:
            break


def test_fall_lands_on_ground():
    body = PhysicsBody(100, 100, 18, 38)
    fall(body, [GROUND])
    assert body.on_ground
    assert body.rect.bottom == GROUND.top
    assert body.vel_y == 0


def test_horizontal_wall_blocks():
    body = PhysicsBody(50, 208, 18, 38)
    body.vel_x = 200
    for _ in range(120):
        body.move_and_collide(DT, [GROUND, WALL], [])
    assert body.rect.right == WALL.left
    assert body.vel_x == 0


def test_one_way_passes_from_below_and_lands_from_above():
    body = PhysicsBody(140, 210, 18, 38)
    body.vel_y = -300
    for _ in range(14):
        body.move_and_collide(DT, [GROUND], [PLATFORM])
    assert body.rect.bottom < PLATFORM.top
    fall(body, [GROUND], [PLATFORM])
    assert body.on_ground
    assert body.ground_is_one_way
    assert body.rect.bottom == PLATFORM.top


def test_drop_through_one_way():
    body = PhysicsBody(140, 152, 18, 38)
    fall(body, [GROUND], [PLATFORM])
    assert body.ground_is_one_way
    body.on_ground = False
    fall(body, [GROUND], [PLATFORM], drop_through=True)
    assert body.rect.bottom == GROUND.top
    assert not body.ground_is_one_way


def test_stays_grounded_across_frames():
    body = PhysicsBody(100, 100, 18, 38)
    fall(body, [GROUND])
    for _ in range(30):
        body.vel_y = min(body.vel_y + config.GRAVITY * DT, config.MAX_FALL)
        body.move_and_collide(DT, [GROUND], [])
        assert body.on_ground
        assert body.rect.bottom == GROUND.top