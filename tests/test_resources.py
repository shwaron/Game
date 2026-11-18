from game.components.resources import ResourcePool


def test_spend_reduces_and_blocks_when_insufficient():
    pool = ResourcePool(100, regen_rate=10, regen_delay=0.5)
    assert pool.spend(30)
    assert pool.value == 70
    assert not pool.spend(80)
    assert pool.value == 70


def test_regen_waits_for_delay_then_clamps_to_max():
    pool = ResourcePool(100, regen_rate=50, regen_delay=0.5)
    pool.spend(40)
    pool.update(0.4)
    assert pool.value == 60
    pool.update(0.2)
    assert pool.value == 70
    pool.update(2.0)
    assert pool.value == 100


def test_refill_restores_full_value():
    pool = ResourcePool(100, regen_rate=10, regen_delay=0.5)
    pool.spend(100)
    pool.refill()
    assert pool.value == 100
    assert pool.spend(100)