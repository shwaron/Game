from game.components.health import Health


def test_damage_and_lethal():
    h = Health(30)
    assert not h.take_damage(10)
    assert h.hp == 20
    assert h.take_damage(25)
    assert h.hp == 0
    assert not h.alive


def test_heal_caps_at_max():
    h = Health(30)
    h.take_damage(10)
    h.heal(100)
    assert h.hp == 30