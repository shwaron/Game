import pytest

from game.components.status_effects import StatusEffects


def test_burn_stacks_dot():
    s = StatusEffects()
    s.apply("burn", 3.0, potency=2.0, max_stacks=3)
    s.apply("burn", 3.0, potency=2.0, max_stacks=3)
    assert s.effects["burn"]["stacks"] == 2
    assert s.update(0.5) == pytest.approx(2.0)


def test_dot_expires():
    s = StatusEffects()
    s.apply("poison", 0.1, potency=5.0)
    s.update(0.2)
    assert not s.has("poison")


def test_freeze_slow_and_stun():
    s = StatusEffects()
    assert s.speed_multiplier() == 1.0
    s.apply("freeze", 1.0)
    assert s.speed_multiplier() == 0.5
    s.apply("stun", 0.5)
    assert s.stunned


def test_shield_absorbs_then_breaks():
    s = StatusEffects()
    s.apply("shield", 5.0, potency=10.0)
    assert s.absorb(4) == 0
    assert s.absorb(10) == 4
    assert not s.has("shield")