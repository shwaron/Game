# 《余烬回环》分工协作指南

> 版本：v0.5
> 更新日期：2026-11-17
> 相关文档：[总览与技术](../GAME_DESIGN.md) · [接口与数据契约](interfaces.md) · [剧情](story.md) · [场景](scenes.md) · [机制](mechanics.md)

本指南用于三人团队并行开发。核心原则：**契约先行、模块隔离、主干可运行、小步提交、文档即真相**。

---

## 1. 团队角色与职责

| 角色 | 代号 | 负责范围 | 主要产出 | 依赖 |
| --- | --- | --- | --- | --- |
| 引擎与框架 | A / Engine | 主循环、场景管理、资源/输入/相机/事件/存档、物理与判定组件、打包、测试基础设施 | 可运行框架、稳定 API、CI 与 exe 构建 | B/C 的数据契约 |
| 玩法与关卡 | B / Gameplay | 玩家/敌人/Boss/弹幕/掉落、战斗/生成/掉落/成长/粒子系统、关卡加载与房间、玩法数据表、Tiled 地图、数值平衡 | 可玩战斗、固定关卡、装备与敌人内容 | A 的框架 API；C 的文本 key |
| 叙事与界面 | C / Narrative & UI | 标题/祭坛/暂停/死亡/设置/图鉴场景、HUD/背包/小地图、剧情与对话数据、本地化、UI 素材与字体、剧情演出 | 完整 UI/UX、剧情呈现、文本与本地化 | A 的场景/事件 API；B 的玩法状态 |

美术与音频为共享产出：

- 场景地块、角色/敌人/Boss 精灵、特效、BGM/音效：B 主导，C 协助 UI 相关素材。
- UI 图标、字体、界面布局：C 主导。
- 资源加载管线与命名校验：A 负责。
- 三人共同遵守 [场景文档](scenes.md) 中的素材规范与命名规则。

---

## 2. 模块所有权（目录边界）

| 目录/文件 | 所有者 | 说明 |
| --- | --- | --- |
| `game/core/` | A | 框架服务，禁止 B/C 直接修改内部实现 |
| `game/components/` | A | 物理、生命、判定框、状态机、状态效果 |
| `tools/build.py`、打包配置 | A | exe 构建与发布 |
| `tests/` 基础设施 | A | pytest 配置、smoke test；B/C 补充各自测试 |
| `game/entities/` | B | 玩家、敌人、Boss、弹幕、掉落 |
| `game/systems/` | B | 战斗、生成、掉落、成长、粒子 |
| `game/world/` | B | 关卡加载、房间、地块、生物群系 |
| `game/data/`（玩法表） | B | weapons/skills/affixes/enemies/biomes/loot_tables |
| `assets/maps/`、`tools/validate_data.py` | B | Tiled 地图与数据校验 |
| `game/scenes/` | C | 场景实现（调用 A 的 SceneManager） |
| `game/ui/` | C | HUD、组件、背包、小地图 |
| `game/data/story.json`、`game/data/localization/` | C | 剧情、对话、文本 |
| `assets/ui/`、`assets/fonts/` | C | UI 素材与字体 |
| `assets/sprites/`、`assets/tiles/`、`assets/fx/`、`assets/audio/` | B/C | 按素材规范产出，A 负责加载 |
| `docs/interfaces.md`、数据 schema | 三人共有 | 契约变更需全员评审 |
| `GAME_DESIGN.md`、`docs/` 其他文档 | 三人共有 | A 汇总维护，B/C 按领域更新 |

规则：

- 不跨目录修改他人负责的代码；需要改动时提 Issue 或 PR 给对应 owner。
- 共享文件（接口、数据 schema、事件名）变更必须三人评审。
- 每个目录的对外接口以 [interfaces.md](interfaces.md) 为准。

---

## 3. 协作原则

1. **契约先行**：先定接口与数据格式，再并行开发；接口未定不写实现。
2. **模块隔离**：通过 API/事件/数据通信，不直接调用他人内部函数。
3. **主干可运行**：`main` 始终保持可启动、可测试；破坏性改动走分支。
4. **小步提交**：一个 PR 聚焦一个任务，便于评审与回滚。
5. **文档即真相**：设计决定、接口变更、平衡调整写入文档，不靠口头约定。
6. **占位优先**：美术/音频先用占位素材，保证玩法与流程可验证。

---

## 4. Git 工作流

### 4.1 分支命名

```text
feat/engine-<描述>      A 的新功能
feat/gameplay-<描述>    B 的新功能
feat/narrative-<描述>   C 的新功能
fix/<模块>-<描述>       缺陷修复
art/<描述>              素材提交
doc/<描述>              文档更新
balance/<描述>          数值调整
```

### 4.2 PR 流程

1. 从 Issue 领取任务，创建分支。
2. 本地开发并跑相关测试。
3. 提交 PR，关联 Issue，说明改动与测试方式。
4. 至少 1 位其他角色评审；涉及共享契约需三人评审。
5. 评审通过后合并到 `main`；合并后删除分支。

### 4.3 主干保护

- `main` 禁止直接 push（后续在 GitHub 开启 branch protection）。
- 合并前要求：PR 评审通过、相关测试通过、无冲突。
- 禁止 force push `main`；冲突用 merge/rebase 解决，不丢弃他人改动。

### 4.4 提交信息规范

采用 Conventional Commits：

```text
feat: 新增玩家冲刺无敌帧
fix: 修复单向平台下穿判定
docs: 更新接口契约中的事件表
art: 添加城郊地块占位图
balance: 调整直剑基础伤害
test: 补充掉落稀有度单元测试
```

### 4.5 CODEOWNERS

仓库根目录提供 `CODEOWNERS` 模板。填入三人 GitHub 用户名后启用，PR 会自动请求对应 owner 评审。

---

## 5. 任务管理

### 5.1 Issue 标签

| 标签 | 含义 |
| --- | --- |
| `area/engine` | A 负责 |
| `area/gameplay` | B 负责 |
| `area/narrative` | C 负责 |
| `type/feature` | 新功能 |
| `type/bug` | 缺陷 |
| `type/art` | 素材 |
| `type/doc` | 文档 |
| `type/balance` | 数值 |
| `priority/high` | 高优先级 |
| `good-first-issue` | 新人上手任务 |

### 5.2 里程碑

沿用 [总览文档](../GAME_DESIGN.md) 的 M0–M7。每个里程碑拆成 1–3 天粒度的 Issue，标注 owner 与验收标准。

### 5.3 完成定义（DoD）

- 代码/素材/文档已提交并通过 PR 评审。
- 相关测试或手动验收清单通过。
- 不破坏 `main` 的可运行性。
- 接口/数据变更已同步到 [interfaces.md](interfaces.md)。

### 5.4 集成节奏

- 每周至少一次集成构建：A 负责确保 `main` 可运行，B/C 验证各自模块。
- 里程碑结束时做完整冒烟测试与打包验证。

---

## 6. 接口与数据契约

所有跨模块通信以 [interfaces.md](interfaces.md) 为唯一依据：

- 核心 API：SceneManager、EventBus、AssetManager、InputManager、SaveManager。
- 事件契约：事件名、payload、发布者、订阅者。
- 数据契约：武器/技能/词缀/敌人/生物群系/掉落/剧情/对话/本地化 JSON 结构。
- 关卡契约：Tiled 图层与对象类型。
- UI 状态契约：Run 向 UI 提供的状态数据。
- 剧情标记契约：story flags 与触发条件。

契约变更流程：

1. 提出变更 Issue，说明影响范围。
2. 三人评审；破坏性变更需版本号升级与迁移方案。
3. 更新 `interfaces.md` 与相关 schema。
4. 各 owner 同步修改实现与测试。

---

## 7. 测试与验收

| 角色 | 测试重点 |
| --- | --- |
| A | 核心服务单元测试、场景切换、存档读写、smoke test、打包验证 |
| B | 战斗判定、掉落/词缀生成、数值公式、关卡可达性校验 |
| C | UI 手动验收清单、本地化完整性、剧情标记触发、对话条件 |

- 每个 PR 至少运行相关测试；数据表改动必须跑 `tools/validate_data.py`。
- 素材改动需检查命名、尺寸、调色板与许可证记录。
- 里程碑验收按总览文档的验收标准执行。

---

## 8. 素材与资源协作

- 命名、尺寸、动画帧数、调色板遵循 [场景文档](scenes.md)。
- 第三方素材记录到 `assets/CREDITS.md`（来源、许可证、用途）。
- AI 素材仅作草案，关键素材人工修整；不模仿具体游戏风格。
- 占位素材统一放 `assets/placeholder/`，正式素材替换时保留命名一致。
- A 提供资源加载与校验工具；B/C 按规范提交素材。

---

## 9. 里程碑分工表

| 里程碑 | A / Engine | B / Gameplay | C / Narrative & UI |
| --- | --- | --- | --- |
| M0 环境 | 环境搭建、依赖验证、CI 基础 | 评审玩法/关卡契约 | 评审剧情/UI 契约 |
| M1 原型 | 主循环、场景管理、输入、物理、相机 | 玩家移动/跳跃/冲刺/攻击、练习场 | 占位 HUD、标题/暂停场景 |
| M2 战斗 | 判定框、生命、状态效果、事件 | 1 武器、2 敌人、战斗/掉落系统 | 伤害数字、拾取提示、死亡结算占位 |
| M3 关卡 | 关卡加载、房间切换、Tiled 集成 | 1 区域手工地图、机关、敌人布置 | 小地图、房间提示、场景演出接口 |
| M4 成长 | 存档、原子写入、迁移 | 余烬结算、解锁、成长系统 | 祭坛/死亡/图鉴场景、剧情标记 |
| M5 内容 | 集成与性能 | 完整区域 + Boss + 6 武器 | 剧情节点、NPC 对话、UI 完善 |
| M6 美术音频 | 资源管线、加载校验 | 场景/角色/敌人素材、BGM/音效 | UI 素材、字体、本地化 |
| M7 打包 | exe/安装包、干净机器测试 | 内容验收、平衡测试 | UI/剧情验收、文本检查 |

---

## 10. 沟通与决策

- Issue/PR 评论是正式记录；重要决定同步到文档。
- 每周一次短同步：进度、阻塞、契约变更、下周任务。
- 跨模块争议先对照 `interfaces.md`；无法解决时三人讨论并记录决定。
- 不私下改共享契约；不绕过评审合并。

---

## 11. 新人上手

1. 阅读 [总览](../GAME_DESIGN.md)、本指南与 [接口契约](interfaces.md)。
2. 按总览文档搭建虚拟环境并安装依赖。
3. 运行 smoke test，确认 `main` 可启动。
4. 领取 `good-first-issue`，走完整 PR 流程。
5. 熟悉自己负责目录的边界与对外接口。

---

## 12. 待补充

- 三人 GitHub 用户名（用于启用 CODEOWNERS 与分支保护）。
- GitHub Projects 任务板与 Issue 模板。
- CI 工作流（pytest + 数据校验 + 打包冒烟）。
- 素材占位包与正式素材替换计划。
