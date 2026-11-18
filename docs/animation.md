# 《余烬回环》像素动画与动作引擎设计

> 版本：v0.5
> 更新日期：2026-11-18
> v0.5 调整：敌人示例改为武侠客栈妖物（`wine_imp` / `paper_runner`）
> 相关文档：[接口与数据契约](interfaces.md) · [机制](mechanics.md) · [场景与素材规范](scenes.md)

本文件定义角色动作分类、动画片段数据契约与 `Animator` 播放器。核心原则：**逻辑判定是权威，动画跟随逻辑**——攻击/受击窗口仍由数据表计时驱动，动画只负责表现，避免帧率与判定耦合。

---

## 1. 动作分类

### 1.1 玩家动作

| 大类 | 动作 id | 对应逻辑状态 | 循环 | 说明 |
| --- | --- | --- | --- | --- |
| 移动 | `idle` | 站立 | 是 | 呼吸/眨眼 |
| 移动 | `run` | 水平速度 > 5 | 是 | 跑步 |
| 移动 | `jump` | 离地且上升 | 否 | 起跳 |
| 移动 | `fall` | 离地且下落 | 是 | 下落 |
| 移动 | `dash` | `dash_time > 0` | 否 | 冲刺，附带残影 |
| 战斗 | `attack_<class>_windup` | `attack_phase == windup` | 否 | 前摇（与武器 `windup_ms` 等长） |
| 战斗 | `attack_<class>_active` | `attack_phase == active` | 否 | 判定帧（与 `active_ms` 等长） |
| 战斗 | `attack_<class>_recovery` | `attack_phase == recovery` | 否 | 后摇（与 `recovery_ms` 等长） |
| 战斗 | `parry` | `parry_timer > 0` | 否 | 弹反窗口（0.15 s） |
| 技能 | `skill` | `cast_timer > 0` | 否 | 施法（0.25 s），移动与受击可打断表现 |
| 受创 | `hurt` | `hurt_timer > 0` | 否 | 受击闪白 |
| 受创 | `death` | 生命 ≤ 0 | 否 | 倒地，停在末帧 |

攻击动作按武器类别细分：`<class>` ∈ `sword / dagger / hammer / spear / staff`，共 15 个片段；玩家 `weapon["class"]` 决定播放哪一套（缺省或未识别类别回退 `sword`）。各片段帧率与对应武器的 `windup_ms / active_ms / recovery_ms` 对齐，保证观感与判定节奏一致。

### 1.2 敌人动作

| 大类 | 动作 id | 对应逻辑状态 | 循环 | 说明 |
| --- | --- | --- | --- | --- |
| 移动 | `idle` | `state == idle` 且静止 | 是 | 待机 |
| 移动 | `walk` | `state == idle` 且有速度 | 是 | 追击/走位 |
| 战斗 | `windup` | `state == windup` | 是 | 攻击前摇，需明显预警 |
| 战斗 | `active` | `state == active` | 是 | 判定帧 |
| 战斗 | `recovery` | `state == recovery` | 是 | 后摇 |
| 受创 | `stagger` | `state == stagger` | 是 | 硬直/受击 |
| 受创 | `death` | 生命 ≤ 0 | 否 | 倒地后移除 |

敌人闪避：数据层预留 `dodge` 动作 id（快速侧移/后撤），M3 起由 `enemies.json` 新招式启用；动画表可先缺省，缺省时回退 `walk`。

---

## 2. 片段数据契约（animations.json）

```json
{
  "schema_version": 1,
  "player": {
    "origin": [17, 2],
    "clips": {
      "idle": {"sheet": "sprites/player/idle.png", "frames": 4, "fps": 6, "loop": true},
      "attack_sword_active": {
        "sheet": "sprites/player/attack_sword_active.png",
        "frames": 4,
        "fps": 50,
        "loop": false,
        "events": [{"frame": 0, "name": "swing_hit"}]
      }
    }
  },
  "enemies": {
    "wine_imp": {"origin": [2, 2], "clips": {"walk": {"sheet": "sprites/enemies/wine_imp/walk.png", "frames": 4, "fps": 8, "loop": true}}}
  }
}
```

规则：

- 图集为**横向条带**：帧宽 = 图片宽 / frames，帧高 = 图片高。
- `origin` 为帧左上角相对实体碰撞框左上角的偏移；默认把帧底边与碰撞框底边对齐。
- `fps` 为每秒帧数；`loop=false` 播放到末帧后停在末帧（`finished=True`）。
- `events` 可选：帧索引进驻时触发一次（进入循环后重置），供音效/特效/弹幕使用；当前 M2 保留接口，判定仍走逻辑计时。
- 缺失动作时的回退链：`idle → walk → 静态单帧`；缺失素材属配置错误，由数据校验脚本报告。

### 2.1 资源路径与尺寸

| 角色 | 目录 | 帧尺寸 |
| --- | --- | --- |
| 玩家 | `assets/sprites/player/<action>.png` | 52×40 |
| 敌人 | `assets/sprites/enemies/<enemy_id>/<action>.png` | 24×36 |

- 占位素材由 `tools/gen_placeholder_sprites.py` 生成：以关节坐标驱动，绘制武侠风黑衣剑客（长发髻、银肩饰、腰带饰、长袍下摆），武器按类别分别绘制（剑含银护手与余烬流苏、枪尖、铁锤、法杖余烬珠），腰后挂鞘。姿态可附 `hair=(dx,dy)` 与 `skirt=dx` 元数据，驱动发辫与袍摆的次级摆动。
- 玩家帧加宽到 52×40 以容纳长剑与挥击轨迹；美术以帧中心为轴排布，`origin` 相应取 `[17, 2]`，使左右朝向翻转时身体、武器与碰撞框保持对齐。
- 正式素材替换时**保持路径与帧数不变**，帧数变化须同步 `animations.json` 并跑校验。
- 当前占位素材预览：[动作总览 GIF](preview/player_actions.gif) · [动作帧总表 PNG](preview/player_actions.png)。
- 朝向：素材默认朝右，绘制时按 `facing < 0` 水平翻转并缓存翻转面。

---

## 3. Animator API（A 提供）

```python
class AnimationClip:
    name: str
    sheet: str
    frames: int
    fps: float
    loop: bool
    origin: tuple[int, int]
    events: list[dict]

class Animator:
    def __init__(self, clips: dict[str, AnimationClip], on_event=None) -> None: ...
    def play(self, name: str, restart: bool = False) -> None: ...
    def update(self, dt: float) -> None: ...
    @property
    def current(self) -> str: ...
    @property
    def frame_index(self) -> int: ...
    @property
    def finished(self) -> bool: ...
    def draw(self, surface, topleft: tuple[int, int], facing: int) -> None: ...
```

- `play` 对同名片段默认不重置；切换片段从第 0 帧开始。
- 事件回调签名 `on_event(name: str, frame: int)`，只在帧进入时触发一次。
- 玩家/敌人在 `update` 末尾按优先级择一调用 `play`，再 `update(dt)`；暂停/顿帧期间整个逻辑冻结，动画自然冻结。

### 3.1 状态优先级

玩家（高 → 低）：`death > hurt > dash > skill > attack_<class>_windup/active/recovery > parry > jump/fall > run > idle`。

敌人（高 → 低）：`death > stagger > windup > active > recovery > walk > idle`。

---

## 4. 与逻辑的同步

| 动画 | 逻辑窗口来源 | 时长（默认） |
| --- | --- | --- |
| `attack_*` | `weapons.json` 的 `windup_ms / active_ms / recovery_ms` | 按武器类别：剑 50/80/140、匕 30/60/90、锤 130/90/300、枪 70/70/160、杖 80/90/170 ms |
| `parry` | 弹反窗口 | 150 ms |
| `skill` | 施法锁 `cast_timer` | 250 ms |
| `hurt` | 受击闪烁 | 250 ms |
| 敌人 `windup/active/recovery` | `enemies.json` 的招式毫秒数 | 数据表 |

- 逻辑先切换阶段，动画在下一帧同步切换；不存在“动画播完才出判定”。
- 若动画时长与逻辑窗口不一致，以逻辑为准（可接受动画截断/停留）。

---

## 5. 后续扩展

- 用事件帧接入脚步声、挥砍音效、弹幕生成（当前保留 `events` 接口）。
- 连击分段：`weapons.json` 的 combo 对应独立片段（`attack1_*`、`attack2_*`）。
- 敌人 `dodge` 动作与精英词缀动画（护盾/狂暴）。
- C 可通过 `Animator.current` 读取当前动作，驱动 UI 或剧情演出。

---

## 6. 版本记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| v0.1 | 2026-11-18 | 初版：动作分类、片段契约、Animator API、玩家/敌人接入方案 |
| v0.2 | 2026-11-18 | 攻击动作按武器类别拆分 15 个片段；新增匕/锤/枪/杖占位帧，剑类资源更名 `attack_sword_*` |
| v0.3 | 2026-11-18 | 玩家/敌人全部占位素材改为火柴人骨骼框架；攻击判定框调试绘制改为细描边 |
| v0.4 | 2026-11-18 | 主角改为武侠风黑衣剑客像素造型：52×40 帧、origin [17,2]、发辫/袍摆次级摆动、挂鞘与分类武器绘制；敌人保留火柴人骨骼占位 |