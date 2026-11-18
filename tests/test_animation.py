from game.core.animation import AnimationClip, Animator, build_clips


def make_clip(
    name: str = "walk",
    frames: int = 4,
    fps: float = 10,
    loop: bool = True,
    events=None,
) -> AnimationClip:
    return AnimationClip(name, "", frames, fps, loop, (0, 0), events)


def test_frame_advance_and_loop():
    anim = Animator({"walk": make_clip()})
    anim.play("walk")
    assert anim.frame_index == 0
    anim.update(0.1)
    assert anim.frame_index == 1
    for _ in range(3):
        anim.update(0.1)
    assert anim.frame_index == 0
    assert not anim.finished


def test_non_loop_clamps_last_frame():
    anim = Animator({"hit": make_clip("hit", frames=2, fps=10, loop=False)})
    anim.play("hit")
    anim.update(0.5)
    assert anim.finished
    assert anim.frame_index == 1


def test_same_clip_does_not_restart_unless_forced():
    anim = Animator({"walk": make_clip()})
    anim.play("walk")
    anim.update(0.1)
    anim.play("walk")
    assert anim.frame_index == 1
    anim.play("walk", restart=True)
    assert anim.frame_index == 0


def test_events_fire_once_per_frame_entry():
    fired = []
    clip = make_clip(
        "hit",
        frames=3,
        loop=False,
        events=[
            {"frame": 0, "name": "start"},
            {"frame": 1, "name": "impact"},
        ],
    )
    anim = Animator(
        {"hit": clip}, on_event=lambda name, frame: fired.append((name, frame))
    )
    anim.play("hit")
    assert fired == [("start", 0)]
    anim.update(0.1)
    assert fired == [("start", 0), ("impact", 1)]
    anim.update(0.1)
    anim.update(0.1)
    assert fired == [("start", 0), ("impact", 1)]


def test_build_clips_applies_origin_and_events():
    clips = build_clips(
        {
            "origin": [7, 2],
            "clips": {
                "idle": {
                    "sheet": "sprites/player/idle.png",
                    "frames": 4,
                    "fps": 6,
                    "loop": True,
                },
                "attack": {
                    "sheet": "sprites/player/attack_active.png",
                    "frames": 4,
                    "fps": 50,
                    "loop": False,
                    "events": [{"frame": 0, "name": "swing_hit"}],
                },
            },
        }
    )
    assert clips["idle"].origin == (7, 2)
    assert clips["attack"].events[0]["name"] == "swing_hit"
    assert clips["idle"].loop
    assert not clips["attack"].loop