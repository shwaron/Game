# 《余烬回环》模块接口与数据契约

> 版本：v0.12
> 更新日期：2026-11-18
> v0.12 调整：新增 `chest.opened` / `manual.learned` 事件、秘籍 HUD 状态；攻击动画改为逐武器片段
> v0.11 调整：剧情标记与对话示例改为武侠主题（灯婆、货郎、焦面掌柜）
> 相关文档：[分工协作指南](collaboration.md) · [总览与技术](../GAME_DESIGN.md) · [机制](mechanics.md) · [场景](scenes.md) · [剧情](story.md)

本文件是三人协作的**唯一接口依据**。A 提供框架 API，B/C 通过 API、事件与数据契约通信。任何契约变更需三人评审，并同步更新本文件。

---

## 1. 核心 API（A 提供）

以下为设计级签名，实现由 A 负责；B/C 只依赖这些接口，不访问内部实现。

### 1.1 SceneManager

```python
class Scene:
    def enter(self) -> None: ...
    def exit(self) -> None: ...
    def handle_event(self, event) -> None: ...
    def update(self, dt: float) -> None: ...
    def draw(self, surface) -> None: ...

class SceneManager:
    def push(self, scene: Scene) -> None: ...
    def pop(self) -> None: ...
    def replace(self, scene: Scene) -> None: ...
    @property
    def current(self) -> Scene: ...
```

规则：

- 场景之间不直接引用，统一通过 SceneManager 切换。
- 暂停/设置等覆盖场景用 `push/pop`；标题→余烬祠→单局用 `replace`。
- `dt` 为固定逻辑步长（1/60 秒）。

### 1.2 EventBus

```python
class EventBus:
    def subscribe(self, event_name: str, callback) -> None: ...
    def unsubscribe(self, event_name: str, callback) -> None: ...
    def publish(self, event_name: str, payload: dict) -> None: ...
```

规则：

- 事件名格式：`domain.action`，全小写，点分隔。
- payload 为字典，发布时传副本，禁止跨模块共享可变对象。
- 跨模块只传 id/数值/文本 key，不直接传实体引用。

### 1.3 AssetManager

```python
def resource_path(rel: str) -> Path: ...
def load_image(rel: str) -> Surface: ...
def load_sound(rel: str) -> Sound: ...
def load_font(rel: str, size: int) -> Font: ...
def load_json(rel: str) -> dict: ...
```

规则：

- 图片加载后 `convert_alpha()`；字体/音效缓存。
- 资源缺失时抛出明确错误，不静默返回占位。
- 打包后路径通过 `resource_path` 解析（兼容 PyInstaller）。

### 1.4 InputManager

```python
def is_action_pressed(action: str) -> bool: ...
def is_action_just_pressed(action: str) -> bool: ...
def get_axis(axis: str) -> float: ...
def rebind(action: str, binding) -> None: ...
```

标准 action：

```text
move_left, move_right, jump, dash, attack, offhand,
skill1, skill2, interact, swap, map, pause, down
```

`down`（S / ↓）用于单向平台下穿，M1 新增，待三人评审确认。

### 1.5 SaveManager

```python
def load_meta() -> dict: ...
def save_meta(data: dict) -> None: ...
def get_save_path() -> Path: ...
```

meta 结构（schema_version 必填）：

```json
{
  "schema_version": 1,
  "embers": 0,
  "unlocks": {"weapons": [], "skills": [], "shortcuts": []},
  "codex": [],
  "max_heat": 0,
  "settings": {},
  "stats": {"deaths": 0, "runs": 0, "best_depth": 0},
  "story_flags": {},
  "ending": null
}
```

规则：原子写入 + 备份；版本迁移由 A 实现；单局进度不存档。

### 1.6 其他服务

- `Camera`：跟随、死区、边界钳制、震动；B 调用，C 不直接操作。
- `AudioManager`：`play_sfx(id)`、`play_bgm(id)`、`stop_bgm()`；B/C 通过 id 调用。
- `Timer`：固定步长累加器；A 内部使用。

### 1.7 Animator（M2 新增）

```python
class Animator:
    def play(self, name: str, restart: bool = False) -> None: ...
    def update(self, dt: float) -> None: ...
    @property
    def current(self) -> str: ...
    @property
    def frame_index(self) -> int: ...
    @property
    def finished(self) -> bool: ...
    def draw(self, surface, topleft, facing: int) -> None: ...
```

- 玩家/敌人在 `update` 末尾按状态优先级调用 `play`，再 `update(dt)`；顿帧/暂停时动画随逻辑冻结。
- 动作分类、优先级与帧事件详见 [动画引擎设计](animation.md)。
- 缺片段时回退 `idle`；B/C 不直接绘制角色，也不自行推进帧。

---

## 2. 事件契约

| 事件名 | payload | 发布者 | 订阅者 |
| --- | --- | --- | --- |
| `player.damaged` | `{amount, source, position}` | B | C（HUD/伤害数字）、A（存档统计） |
| `player.died` | `{run_id, depth, cause}` | B | A（结算）、C（死亡场景） |
| `enemy.killed` | `{enemy_id, position, loot_table}` | B | B（掉落）、C（图鉴） |
| `room.entered` | `{room_id, biome, room_type}` | B | C（小地图/提示） |
| `anchor.lit` | `{room}` | B（房间/灯锚） | C（舆图通知/音效） |
| `chest.opened` | `{room, weapon, level}` | B（宝箱/房间） | C（开箱提示/音效） |
| `manual.learned` | `{stat, value}` | B（秘籍选择） | C（提示/面板刷新） |
| `loot.picked` | `{item_id, rarity, slot}` | B | C（拾取提示/背包） |
| `run.ended` | `{outcome, embers, depth}` | B | A（存档）、C（结算 UI） |
| `boss.phase` | `{boss_id, phase}` | B | C（演出/台词） |
| `story.flag` | `{key, value}` | B/C | C（剧情/对话） |
| `ui.notify` | `{text_key, params}` | B/C | C（通知） |

规则：

- 新增事件必须在本表登记，注明 payload 与发布/订阅方。
- 事件不保证顺序；需要顺序的逻辑用状态机或显式调用。
- 禁止在事件回调中直接修改其他模块内部状态。

---

## 3. 数据契约（JSON）

通用规则：

- UTF-8 编码，键名 `snake_case`。
- 显示文本一律用 localization key，不写死中文。
- 每个数据文件带 `schema_version`。
- 所有数据表由 `tools/validate_data.py` 校验（B 维护，A/C 评审）。

### 3.1 weapons.json

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 唯一标识 |
| name_key / desc_key | string | 本地化 key |
| class | string | sword/dagger/hammer/spear/bow/staff/chakram/shield |
| base_damage | number | 基础伤害 |
| attack_speed | number | 攻速倍率 |
| combo | number[] | 连击倍率 |
| hitbox | [w, h] | 攻击框 |
| windup_ms / active_ms / recovery_ms | number | 帧窗口 |
| knockback | number | 击退 |
| max_level | number | 等级上限（默认 5；M2 新增） |
| level_scale | number | 每级伤害增量（默认 0.1；M2 新增） |
| scaling | object[] | 属性绑定 `{stat, max_bonus}`，stat 为 missing_hp/hp/stamina/mana（M2 新增） |
| tags | string[] | melee/ranged/starter 等 |

运行时武器实例另带 `id` 与 `level`（不写入 JSON）。伤害计算由 `game/systems/weapons.py` 的 `weapon_damage(weapon, player)` 提供：

```text
伤害 = base_damage × (1 + level_scale × (level − 1)) × (1 + Σ max_bonus × 属性比例)
```

武器比例定义：`missing_hp = 1 − hp/max_hp`，`hp = hp/max_hp`，`stamina/mana = 当前/上限`。

示例见 [武器系统](weapons.md)。

### 3.2 skills.json

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 唯一标识 |
| name_key / desc_key | string | 本地化 key |
| type | string | aoe/dash/dot/control/summon/buff |
| cooldown | number | 秒 |
| mana_cost | number | 蓝条消耗（M2 新增） |
| damage | number | 基础伤害（可为 0） |
| radius | number | AOE 半径（像素，非 AOE 技能可省略；M2 新增） |
| effects | object[] | 附加状态/位移/召唤参数 |
| rarity | string | common/fine/rare/epic/legendary |
| tags | string[] | 分类标签 |

### 3.3 affixes.json

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 唯一标识 |
| name_key | string | 本地化 key |
| stat | string | damage/attack_speed/crit/lifesteal/burn/freeze/armor_pen 等 |
| min / max | number | 数值区间 |
| slots | string[] | weapon/skill/amulet/relic |
| weight | number | 抽取权重 |
| unique | bool | 是否独特（传说专属） |

### 3.4 enemies.json

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 唯一标识 |
| name_key | string | 本地化 key |
| biome | string | 所属区域 |
| hp / damage / armor / speed | number | 基础数值 |
| attacks | object[] | 招式（前摇/判定/后摇/伤害） |
| elite_affixes | string[] | 可附加精英词缀 |
| loot_table | string | 掉落表 id |
| sprite | string | 资源路径 |

### 3.5 biomes.json

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 唯一标识 |
| name_key | string | 本地化 key |
| rooms | string[] | 房间地图 id 列表（固定顺序） |
| entry / exit | string | 入口/出口房间 |
| boss | string | Boss id |
| hazards | string[] | 机关类型 |
| palette | string | 调色板 id |
| bgm | string | 音乐 id |

### 3.6 loot_tables.json

```json
{
  "schema_version": 1,
  "tables": {
    "rat_basic": {
      "entries": [
        {"item": "fire_seed", "weight": 70},
        {"item": "weapon_random", "weight": 25, "rarity_weights": {"common": 60, "fine": 25, "rare": 10, "epic": 4.5, "legendary": 0.5}},
        {"item": "potion", "weight": 5}
      ],
      "guarantee": {"after_rooms": 3, "min_rarity": "rare"}
    }
  }
}
```

### 3.7 story.json

```json
{
  "schema_version": 1,
  "flags": {
    "met_moth": {"type": "bool", "default": false},
    "proof_door": {"type": "bool", "default": false},
    "death_count": {"type": "int", "default": 0}
  },
  "nodes": [
    {
      "id": "intro_wake",
      "type": "dialogue",
      "text_key": "story.intro_wake",
      "conditions": {"loop_count": 0},
      "flags_set": {"met_lamp_keeper": true},
      "next": "tutorial_move"
    }
  ]
}
```

### 3.8 dialogue.json

```json
{
  "schema_version": 1,
  "dialogues": {
    "lamp_keeper_first": {
      "speaker": "lamp_keeper",
      "lines": [
        {"text_key": "dialogue.lamp_keeper_first_1", "condition": null},
        {"text_key": "dialogue.lamp_keeper_first_2", "condition": {"death_count_gte": 1}}
      ]
    }
  }
}
```

### 3.9 localization

- `game/data/localization/zh_CN.json`、`en.json`：扁平 `key → string`。
- 缺失 key 回退到 zh_CN，并记录警告。
- key 命名：`domain.object.field`，如 `weapon.worn_flame_blade.name`。

### 3.10 animations.json

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| schema_version | number | 必填 |
| player / enemies | object | 实体动画集合；`enemies` 键为 enemy_id |
| origin | [dx, dy] | 帧左上角相对实体碰撞框左上角的偏移 |
| clips | object | 动作 id → 片段 |
| clips.*.sheet | string | 相对 `assets/` 的横向条带图路径 |
| clips.*.frames | number | 帧数（图片宽度等分） |
| clips.*.fps | number | 播放帧率 |
| clips.*.loop | bool | 是否循环；非循环停在末帧 |
| clips.*.events | object[] | 帧事件 `{frame, name}`，可选 |

规则见 [动画引擎设计](animation.md)；主角占位帧为武侠风黑衣剑客像素造型（52×40，`origin [17,2]`），敌人为火柴人骨骼占位，均由 `tools/gen_placeholder_sprites.py` 生成；替换正式素材须保持路径与帧数。

攻击片段优先使用 `attack_<weapon_id>_windup/active/recovery`，六把初始武器各一套，缺失时回退 `attack_<class>_*`；跃击为 `plunge_<weapon_id>`，缺失回退 `fall`。新增武器须同步提供三类片段或在数据校验中登记回退。

---

## 4. 关卡数据契约（Tiled）

图层（固定顺序）：

```text
background, terrain, platform_one_way, hazard, decor, entities, foreground
```

对象类型：

| 类型 | 用途 | 关键属性 |
| --- | --- | --- |
| `player_spawn` | 玩家出生点 | 每图唯一 |
| `enemy_spawn` | 敌人出生点 | enemy_id, elite(bool) |
| `boss_spawn` | Boss 出生点 | boss_id |
| `chest` | 宝箱 | loot_table, locked(bool) |
| `exit` | 房间出口 | target_room, direction |
| `door` | 门/闸门 | condition, target_room |
| `shortcut` | 捷径 | unlock_flag |
| `event` | 局内事件 | event_id, choices |
| `npc` | NPC | npc_id, dialogue_id |
| `checkpoint` | 检查点 | biome |

规则：

- 每张地图必须有 `player_spawn` 与至少一个 `exit`。
- 房间连接通过 `exit.target_room` 与 `biomes.json` 校验。
- 对象属性用 Tiled 自定义属性填写，B 维护校验脚本。

---

## 5. UI 状态契约

Run（B）向 UI（C）提供只读状态字典，C 不直接修改玩法状态：

```python
hud_state = {
    "hp": int,
    "max_hp": int,
    "stamina": {"value": float, "max": float},
    "mana": {"value": float, "max": float},
    "potions": int,
    "embers": int,
    "fire_seeds": int,
    "skills": [{"id": str, "cooldown": float, "ready": bool}],
    "weapon": {
        "id": str,
        "name_key": str,
        "rarity": str,
        "level": int,
        "damage": float,
        "scaling_bonus": float,
    },
    "buffs": [{"id": str, "stacks": int}],
    "manual": {"attack": int, "hp": int, "armor": int},
    "room": {"id": str, "biome": str},
}
```

- `manual` 为本局秘籍累计加成，死亡/重开后清零；HUD 在武器栏下方显示「秘籍 攻+X 血+X 御+X」。
- 宝箱开启状态按 `(room_id, x)` 记录在本局，不写入存档；秘籍选择期间游戏暂停。

背包/装备对比数据结构由 C 定义，B 提供物品实例数据（id、词缀、数值）。

---

## 6. 剧情标记契约

| flag | 类型 | 触发 |
| --- | --- | --- |
| `met_lamp_keeper` | bool | 序章灯婆对话 |
| `met_peddler` | bool | 客栈货郎老柴 |
| `met_moth` | bool | 药王谷墨蛾 |
| `proof_door` | bool | 击败焦面掌柜 |
| `proof_memory` | bool | 击败药人母 |
| `proof_time` | bool | 击败守钟僧 |
| `death_count` | int | 每次死亡 +1 |
| `loop_count` | int | 每次回环 +1 |
| `ending_chosen` | string | A/B/C |

对话条件支持：`flag == value`、`death_count_gte`、`loop_count_gte`、`item_owned`。C 负责条件解析，B 负责在玩法节点发布 `story.flag`。

---

## 7. 资源命名与加载

- 命名规范见 [场景文档](scenes.md) 4.3。
- 资源路径相对 `assets/`，如 `sprites/player_idle_01.png`。
- A 提供加载与缓存；B/C 按规范提交素材，不自行实现加载逻辑。
- 第三方素材记录到 `assets/CREDITS.md`。

---

## 8. 契约变更流程

1. 提 Issue 说明变更与影响范围。
2. 三人评审；破坏性变更需升级 `schema_version` 并提供迁移方案。
3. 更新本文件与相关数据 schema。
4. 各 owner 同步修改实现与测试。
5. 合并后通知全员，避免基于旧契约开发。

---

## 9. 版本记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| v0.5 | 2026-11-18 | 初版：核心 API、事件、数据、关卡、UI、剧情标记契约 |
| v0.6 | 2026-11-18 | skills.json 增加 mana_cost/radius；HUD 状态增加体力/蓝条（待三人评审） |
| v0.7 | 2026-11-18 | 新增 Animator 接口与 animations.json 契约；占位像素帧生成器（待三人评审） |
| v0.8 | 2026-11-18 | weapons.json 增加 max_level/level_scale/scaling；weapon_damage 计算与原语；HUD weapon 增加 level/damage/scaling_bonus（待三人评审） |
| v0.9 | 2026-11-18 | 玩家攻击动画片段改为 `attack_<class>_windup/active/recovery`（5 类共 15 个）；weapon 的 class 决定动作模组（待三人评审） |
| v0.10 | 2026-11-18 | 主角动画帧扩为 52×40、origin [17,2]；占位主角改为武侠风像素造型；攻击命中框调试绘制由 `config.DEBUG_HITBOXES` 控制（默认关闭） |
| v0.11 | 2026-11-18 | 剧情标记与对话示例改为武侠主题（灯婆、货郎、焦面掌柜） |
| v0.12 | 2026-11-18 | 新增 `chest.opened` / `manual.learned` 事件；HUD 状态增加 `manual`；攻击动画改为 `attack_<weapon_id>_*` 并保留类别回退；新增 `plunge_<weapon_id>` |
