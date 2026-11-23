# 《余烬回环》游戏设计总览与技术文档（GDD v0.6）

> 状态：原型阶段（M2 战斗与第一关"竹坞客栈"切片已可运行）
> 更新日期：2026-11-18
> v0.6 调整：世界观改为中国古代武侠，第一关改为青篁岭竹海与竹坞客栈
> v0.5 调整：面向三人团队分工协作，新增协作指南、接口契约与目录所有权
> 目标平台：Windows PC（单人）
> 类型：2D 横版动作 + Roguelite（固定关卡、像素风）

---

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [剧情设计](docs/story.md) | 世界观、回环规则、主角设定、NPC、剧情走向、结局与对白 |
| [场景与关卡](docs/scenes.md) | 单局区域结构、固定关卡设计、美术音频规格、素材工具 |
| [机制与系统](docs/mechanics.md) | 核心系统、玩法循环、操作、装备、敌人与 Boss、UI |
| [分工协作指南](docs/collaboration.md) | 三人角色、目录所有权、Git/任务工作流、里程碑分工 |
| [接口与数据契约](docs/interfaces.md) | 核心 API、事件、数据 schema、关卡/UI/剧情标记契约 |
| 本文档 | 项目概述、技术选型、架构、目录结构、打包发布、里程碑与风险 |

---

## 1. 项目概述

| 项目 | 内容 |
| --- | --- |
| 暂定名称 | 《余烬回环》（英文代号 Emberloop） |
| 核心体验 | 高速横版战斗、手工固定关卡、死亡后永久成长 |
| 参考品类 | 《死亡细胞》《哈迪斯》《空洞骑士》的**机制思路**（不复制其美术、剧情、名称） |
| 单局时长 | 20–35 分钟 |
| 全流程时长 | 首次通关约 8–12 小时，后续解锁难度循环 |
| 美术风格 | 16×16 像素地块，玩家 52×40 / 敌人 24×36 占位帧，武侠夜岭 + 灯火点缀 |
| 内部分辨率 | 逻辑 480×270（16:9），绘制层按 2 倍渲染（960×540），默认输出 1440×810 |
| 输入 | 键盘 + 鼠标；预留 Xbox 手柄支持 |
| 语言 | 简体中文优先，数据层预留英文 |

### 一句话概念

> 你是一个在"灯灭之夜"死去的无名游侠，被余烬祠的灯婆以一点灯芯重新捏成人形；
> 每次死亡都会忘记这一轮的一切，但烬心会留下你的"余烬"，让你下一次走进竹坞客栈时走得更远。

### 设计支柱

1. **手感优先**：移动、跳跃、攻击、受击反馈必须先"爽"，再谈内容量。
2. **死亡有意义**：单局失去装备与进度，但余烬永久保留，死亡也在推进。
3. **构筑多样**：武器 + 技能 + 词缀 + 遗物组合产生流派差异，而不是单纯数值堆叠。
4. **固定的世界**：关卡手工设计且布局固定，玩家能记住地形、机关与敌人站位，用熟练度而非运气推进。
5. **可读的像素美学**：暗背景、高对比火光、清晰的攻击预警，保证战斗信息可读。
6. **内容可控**：手工打磨固定关卡，用少量高质量场景支撑多次挑战，避免无限扩张。

---

## 2. 当前环境现状（已完成）

| 项目 | 值 |
| --- | --- |
| Python | 3.13.11（`E:\Python\python313\python.exe`） |
| 虚拟环境 | `E:\Vscode\Demo\.venv` |
| 包管理 | pip 26.3 |
| 验证结果 | pygame 初始化、显示表面、依赖导入均通过 |

已安装依赖：

| 包 | 版本 | 用途 |
| --- | --- | --- |
| pygame-ce | 2.5.8 | 游戏框架（渲染、输入、音频、精灵） |
| pytmx | 3.32 | 读取 Tiled 地图 |
| opensimplex | 0.4.5.1 | 程序化噪声（固定配置的装饰效果） |
| numpy | 2.5.5 | 数值计算、像素级处理（surfarray） |
| pillow | 13.0.0 | 图片处理（切图、图标生成） |
| pyinstaller | 6.22.3 | 打包 exe |
| pytest | 9.2.0 | 单元测试 |

常用命令（Windows）：

```bat
:: 激活虚拟环境（cmd）
.venv\Scripts\activate.bat
:: 激活虚拟环境（PowerShell）
.venv\Scripts\Activate.ps1
:: 直接运行
.venv\Scripts\python.exe main.py
```

> 注意：`.venv/`、`build/`、`dist/` 已写入 `.gitignore`，不会被自动上传任务推送到仓库。

---

## 3. 技术选型

### 3.1 为什么用 pygame-ce

- 成熟稳定，2D 像素游戏的事实标准之一，社区资料多。
- 直接操作 `Surface` 与 `Rect`，像素级缩放（`scale` + nearest）简单可控。
- 与 PyInstaller 兼容性好，打包 exe 成本低。
- 音频、手柄、字体支持齐全，足够完成本项目。
- pygame-ce 是 pygame 的活跃社区分支，修复多、性能更好。

### 3.2 其他选型的取舍

| 方案 | 结论 | 原因 |
| --- | --- | --- |
| arcade | 不采用 | 依赖 OpenGL，打包与老机器兼容性风险更高 |
| pyglet | 不采用 | 需要自己搭更多基础设施，收益低 |
| Godot / Unity | 不采用 | 用户明确要求 Python 技术栈 |
| Panda3D | 不采用 | 偏 3D，2D 工作流不顺手 |

### 3.3 辅助库职责

- **pytmx**：加载 Tiled 导出的 `.tmx`，负责地块、对象层、出生点。
- **opensimplex**：仅用于装饰性氛围（雾、竹叶与灯灰），不影响关卡布局；使用固定配置，保证同一房间每次呈现一致。
- **numpy**：粒子批量计算、画面特效（可选）、测试中的数值校验。
- **pillow**：素材切图脚本、图标处理、截图导出。
- **pytest**：数值公式、词缀生成、存档读写的单元测试。

---

## 4. 总体架构

```text
main.py
  └─ Game (App)
       ├─ SceneManager（场景栈）
       │    ├─ TitleScene      标题
       │    ├─ HubScene        余烬祠（局外成长）
       │    ├─ RunScene        单局游戏
       │    ├─ PauseScene      暂停
       │    ├─ DeathScene      死亡结算
       │    ├─ SettingsScene   设置
       │    └─ CodexScene      图鉴/剧情收集
       ├─ Services（全局服务）
       │    ├─ AssetManager    图片/字体/音效缓存
       │    ├─ AudioManager    音乐/音效通道
       │    ├─ InputManager    键位映射、输入缓冲
       │    ├─ SaveManager     存档（原子写入）
       │    └─ EventBus        简单发布/订阅
       └─ Run（单局世界）
            ├─ WorldMap        固定关卡与区域连接
            ├─ Room / TileMap  当前房间与碰撞
            ├─ Entities        玩家、敌人、弹幕、掉落
            ├─ Systems         战斗、状态、掉落、粒子
            └─ UI              HUD、小地图、背包
```

### 4.1 游戏循环

- 固定逻辑步长 60 Hz（`dt = 1/60`），渲染跟随刷新率。
- 累加器模式：`accumulator += frame_dt`，每满 `1/60` 执行一次 `update()`，避免不同帧率下速度不一致。
- 单帧 `dt` 上限 0.1 秒，防止窗口拖动后"瞬移"。
- 渲染流程：绘制到 480×270 内部 Surface → 整数倍放大 → 输出窗口。

### 4.2 场景管理

- 场景栈：`push/pop/replace`，暂停界面以栈形式覆盖在运行场景之上。
- 每个场景实现 `enter() / exit() / handle_event() / update(dt) / draw(surface)`。
- 场景切换统一走 `SceneManager`，禁止场景内部互相直接引用。

### 4.3 实体设计（轻量组件）

不引入重型 ECS，采用"精灵 + 组件混入"：

- `PhysicsBody`：速度、重力、地面检测、单向平台。
- `Health`：生命、无敌帧、受击硬直、死亡回调。
- `Hitbox / Hurtbox`：攻击框与受击框，带帧窗口。
- `StateMachine`：玩家与 Boss 的行为状态（待机/移动/攻击/硬直/死亡）。
- `StatusEffects`：燃烧、冰冻、中毒、流血、眩晕、护盾。
- `LootDropper`：掉落表与稀有度权重。

### 4.4 数据驱动

武器、敌人、词缀、关卡配置、剧情文本全部放在 `game/data/*.json`，代码只读数据：

- 改数值不碰代码，便于平衡。
- 开发期支持热重载（按 F5 重新读表）。
- 后续可让非程序成员参与填表。

---

## 5. 规划中的目录结构

```text
Demo/
├─ .venv/                     虚拟环境（不入库）
├─ main.py                    入口
├─ requirements.txt           依赖清单
├─ GAME_DESIGN.md             总览与技术文档
├─ CODEOWNERS                 目录评审所有权模板（待填用户名）
├─ .gitignore
├─ docs/
│  ├─ story.md                剧情与角色设计
│  ├─ scenes.md               场景、关卡、美术与音频
│  ├─ mechanics.md            玩法、系统、装备与敌人
│  ├─ collaboration.md        三人分工协作指南
│  └─ interfaces.md           模块接口与数据契约
├─ game/
│  ├─ __init__.py
│  ├─ config.py               常量、分辨率、路径
│  ├─ core/
│  │  ├─ app.py               主循环
│  │  ├─ hd.py                2 倍绘制层（逻辑坐标 → 高分辨率画布）
│  │  ├─ scene_manager.py
│  │  ├─ asset_manager.py
│  │  ├─ audio.py
│  │  ├─ input.py
│  │  ├─ camera.py
│  │  ├─ event_bus.py
│  │  └─ save.py
│  ├─ scenes/
│  │  ├─ title.py
│  │  ├─ hub.py
│  │  ├─ run.py
│  │  ├─ pause.py
│  │  ├─ death.py
│  │  ├─ settings.py
│  │  └─ codex.py
│  ├─ entities/
│  │  ├─ player.py
│  │  ├─ enemy.py
│  │  ├─ boss.py
│  │  ├─ projectile.py
│  │  └─ pickup.py
│  ├─ components/
│  │  ├─ physics.py
│  │  ├─ health.py
│  │  ├─ hitbox.py
│  │  ├─ state_machine.py
│  │  └─ status_effects.py
│  ├─ systems/
│  │  ├─ combat.py
│  │  ├─ spawn.py
│  │  ├─ loot.py
│  │  ├─ progression.py
│  │  └─ particles.py
│  ├─ world/
│  │  ├─ level_loader.py      固定关卡加载与切换
│  │  ├─ world_map.py         区域连接与捷径状态
│  │  ├─ room.py
│  │  ├─ tilemap.py
│  │  └─ biome.py
│  ├─ ui/
│  │  ├─ hud.py
│  │  ├─ widgets.py
│  │  ├─ inventory.py
│  │  └─ minimap.py
│  └─ data/
│     ├─ weapons.json
│     ├─ skills.json
│     ├─ affixes.json
│     ├─ enemies.json
│     ├─ biomes.json
│     ├─ loot_tables.json
│     ├─ story.json
│     └─ localization/
│        ├─ zh_CN.json
│        └─ en.json
├─ assets/
│  ├─ sprites/                角色、敌人、Boss
│  ├─ tiles/                  地块图集
│  ├─ ui/                     界面素材
│  ├─ fx/                     粒子、特效
│  ├─ audio/
│  │  ├─ bgm/
│  │  └─ sfx/
│  ├─ maps/                   Tiled .tmx/.tsx
│  └─ fonts/
├─ tools/
│  ├─ slice_sheets.py         切图脚本
│  ├─ build.py                打包脚本
│  └─ validate_data.py        数据表校验
└─ tests/
   ├─ test_combat.py
   ├─ test_loot.py
   └─ test_save.py
```

---

## 6. 分工协作

本项目按三人团队并行开发设计，详细规则见 [分工协作指南](docs/collaboration.md) 与 [接口契约](docs/interfaces.md)。

| 角色 | 代号 | 成员 | 负责目录 | 核心产出 |
| --- | --- | --- | --- | --- |
| 引擎与框架 | A | shwaron | `game/core/`、`game/components/`、打包与测试基础设施 | 可运行框架、稳定 API、exe 构建 |
| 玩法与关卡 | B | 0range03 | `game/entities/`、`game/systems/`、`game/world/`、玩法数据表、`assets/maps/` | 战斗、固定关卡、装备与敌人内容 |
| 叙事与界面 | C | shuoyu04 | `game/scenes/`、`game/ui/`、剧情/本地化数据、`assets/ui/`、`assets/fonts/` | UI/UX、剧情呈现、文本与本地化 |

协作要点：

- 契约先行：跨模块通信只走 [interfaces.md](docs/interfaces.md) 定义的 API、事件与数据格式。
- 模块隔离：不跨目录改他人代码；共享契约变更需三人评审。
- 主干可运行：`main` 始终可启动、可测试；功能走分支 + PR。
- 目录所有权：`CODEOWNERS` 已启用三人所有权（shwaron / 0range03 / shuoyu04）。
- 里程碑分工：见协作指南第 9 节。

---

## 7. 打包成 exe 方案

### 7.1 方案选择

推荐 **PyInstaller onedir（文件夹模式）**：

- 启动快，资源加载简单，杀毒误报概率低于 onefile。
- 最终以压缩包或安装器分发。
- onefile 作为备选，仅在确实需要单文件时启用（启动慢、易误报）。

### 7.2 打包命令（规划）

```bat
.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed ^
  --name Emberloop ^
  --icon assets\icon.ico ^
  --add-data "assets;assets" ^
  --add-data "game\data;game\data" ^
  main.py
```

### 7.3 工程要点

- 资源路径统一封装：

```python
import sys
from pathlib import Path

def resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel
```

- 存档写到 `%APPDATA%\Emberloop\`，不写 exe 目录。
- 关闭控制台（`--windowed`），异常写入日志文件，启动崩溃时弹窗提示。
- 不启用 UPX，降低杀软误报。
- 添加版本信息文件（公司、产品名、版本号、版权）。
- 可选：用 Inno Setup 制作安装包，附带开始菜单快捷方式与卸载器。
- 发布前在**干净 Windows 虚拟机**测试：无 Python 环境、无开发目录依赖。

### 7.4 打包检查清单

- [ ] 窗口图标与 exe 图标正确
- [ ] 字体、音效、地图、数据表全部随包携带
- [ ] 中文显示正常
- [ ] 存档路径正确，卸载后数据保留策略明确
- [ ] 首次启动无控制台窗口、无报错
- [ ] 杀毒软件扫描无误报
- [ ] 帧率稳定 60 FPS
- [ ] 手柄热插拔正常（如支持）

---

## 8. 里程碑规划

| 阶段 | 目标 | 交付物 | 验收标准 |
| --- | --- | --- | --- |
| M0 环境 | 环境与设计 | 设计文档（总览 + 剧情/场景/机制 + 协作/接口）、venv、依赖 | 依赖可导入，文档通过确认 |
| M1 原型 | 手感验证 | 移动/跳跃/冲刺/攻击、练习场 | 操作跟手，60 FPS |
| M2 战斗 | 核心循环 | 1 武器、2 敌人、血量/受击/掉落 | 能完成一场 30 秒战斗 |
| M3 关卡 | 固定关卡搭建 | 1 个区域的手工地图（Tiled）+ 房间切换 | 主/支路可走通，出生点与出口校验通过 |
| M4 成长 | Meta 系统 | 余烬祠、余烬、解锁、存档 | 死亡→结算→解锁→再开一局闭环 |
| M5 内容 | 垂直切片 | 1 完整区域 + 1 Boss + 6 武器 | 单局 15–20 分钟可玩 |
| M6 美术音频 | 风格化 | 替换占位素材、BGM/音效 | 视觉统一、信息可读 |
| M7 打包 | 发布 | exe + 安装包 + 测试报告 | 干净机器可运行 |

> MVP 建议范围：1 个区域（青篁岭·竹坞客栈）+ 1 个 Boss（焦面掌柜）+ 6 把武器 + 4 种妖物 + 基础 meta 成长。
> 先做"好玩的 15 分钟"，再扩充内容。

---

## 9. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 范围失控 | 项目做不完 | 严格执行 MVP，先垂直切片后扩内容 |
| 固定地图缺乏新鲜感 | 重复游玩动力不足 | 用装备/精英词缀/事件/热度提供变化，持续补充隐藏要素与剧情内容 |
| 手感不佳 | 核心体验失败 | M1 就做练习场，优先调移动/攻击/受击反馈 |
| 美术工作量 | 进度拖延 | 先用占位素材，AI 辅助概念，统一调色板 |
| AI 素材不一致 | 风格割裂 | 限制 AI 只做草案，关键素材人工精修 |
| PyInstaller 误报 | 无法分发 | onedir + 不压缩 + 版本信息；必要时代码签名 |
| 性能问题 | 掉帧 | 内部低分辨率渲染、对象池、限制粒子数量 |
| 存档损坏 | 玩家流失 | 原子写入 + 备份 + 版本迁移 |
| 版权风险 | 下架/纠纷 | 全部原创命名与美术；参考品类机制但不复制表达 |
| 数值失衡 | 体验崩坏 | 数据驱动 + 自动化模拟测试（后期） |

---

## 10. 待确认事项

在开始写代码前，需要确认以下选择：

1. **游戏名称**：是否采用《余烬回环》/ Emberloop，还是你有其他想法？
2. **语言**：只做简体中文，还是中英双语？
3. **美术来源**：自己画、AI 生成辅助、购买素材包，还是先全部用占位色块？
4. **手柄**：MVP 是否需要手柄支持？
5. **分辨率**：480×270（更"像素"）还是 640×360（更清晰、UI 空间更大）？
6. **MVP 范围**：是否同意先做"1 区域 + 1 Boss + 6 武器"的垂直切片？
7. **关卡设计**：固定关卡的白盒布局由我先出草稿和地图示意图，你再提修改意见，是否可以？
8. **剧情基调**：当前是"悲凉但不绝望 + 三结局"的设计，主角真名"沈烬"与"以身代灯"真结局是否保留？
9. **团队信息**：已确认 shwaron = A 引擎、0range03 = B 玩法、shuoyu04 = C 叙事；CODEOWNERS 与 main 分支保护均已启用。

确认后，下一步将进入 **M1 原型阶段**：搭建主循环、场景管理、玩家移动与练习场，不直接开始堆内容。
