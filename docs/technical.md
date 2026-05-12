# 技术文档

本文档说明“生活技能教学 TextWorld Web 游戏”的系统设计、核心流程、API、随机生成机制、前端交互和验证方法，便于项目交付、答辩和后续维护。

## 1. 项目目录结构

```text
textworld/
├─ app.py                         # Flask 后端、TextWorld 生成、命令处理、API
├─ README.md                      # 项目简介和快速运行说明
├─ test_api.py                    # 简单接口冒烟测试脚本
├─ templates/
│  └─ index.html                  # 单页 Web UI、前端状态管理和交互逻辑
├─ games/
│  ├─ cooking_easy.json           # 早期/示例游戏文件
│  ├─ fire_safety_easy.json       # 早期/示例游戏文件
│  ├─ garbage_sorting_easy.json   # 早期/示例游戏文件
│  └─ generated/
│     └─ <game_id>.json           # 每局随机生成的 TextWorld .json 游戏文件
├─ docs/
│  ├─ deployment.md               # 部署文档
│  └─ technical.md                # 技术文档
├─ textworld_env/                 # 可选虚拟环境目录
└─ vendor/                        # 可选本地依赖或第三方资源目录
```

当前主要功能集中在 `app.py` 和 `templates/index.html`：

- `app.py` 负责真实 TextWorld 环境生成、会话状态、中文命令映射、进度计算和 API。
- `templates/index.html` 负责场景选择、游戏画面、目标进度、地图、背包、命令输入、日志和提示按钮。

## 2. 系统架构

整体链路如下：

```text
浏览器 Web UI
   ↓ HTTP/JSON
Flask API(app.py)
   ↓ GameMaker / Game.save
TextWorld .json 游戏文件
   ↓ textworld.start / env.step
TextWorld Environment
   ↓ 状态、分数、facts、inventory
Flask API 整理中文响应
   ↓ JSON
浏览器渲染房间、地图、目标、日志、提示
```

### 2.1 前端职责

- 展示开始页、场景选择页、游戏页。
- 调用 `/api/scenarios` 获取场景和难度。
- 调用 `/api/generate` 创建新游戏。
- 调用 `/api/game/<id>/command` 执行玩家命令。
- 渲染：房间描述、目标进度、背包、地图、命令日志。
- 将部分常用中文输入转换为后端更稳定识别的命令文本。
- 通过“查看提示”按钮按需展示下一步，默认不暴露具体操作。

### 2.2 后端职责

- 定义三类场景、房间库、目标池、难度配置。
- 使用随机 seed 生成房间、地图连接、目标、物品位置。
- 使用 TextWorld `GameMaker` 创建真实游戏。
- 使用 `Game.save()` 保存 `.json` 文件。
- 使用 `textworld.start()` 启动环境。
- 将中文命令映射为 TextWorld 或项目内部多步骤动作。
- 管理 `game_sessions` 中的内存会话状态。
- 返回结构化 JSON 给前端。

## 3. API 说明

### 3.1 `GET /`

返回 Web UI 页面，即 `templates/index.html`。

### 3.2 `GET /api/engine`

检查 TextWorld 引擎状态。

返回字段示例：

```json
{
  "available": true,
  "engine": "textworld-json",
  "textworldVersion": "1.7.0",
  "twMake": "...",
  "zMachine": "当前使用原生 .json 环境；如需传统 Z-machine 文件，需要额外配置 Inform。",
  "error": null
}
```

用途：

- 判断 TextWorld 是否安装和可导入。
- 确认当前运行模式是 `.json` Environment。
- 排查部署问题。

### 3.3 `GET /api/scenarios`

返回三类场景和难度配置。

场景：

- `cooking`：烹制菜品。
- `fire_safety`：防患火灾隐患。
- `garbage_sorting`：垃圾分类。

难度：

- `easy`
- `medium`
- `hard`

接口会补充中文难度名称和场景描述，供前端选择卡片使用。

### 3.4 `POST /api/generate`

创建新游戏。

请求体：

```json
{
  "scenario": "cooking",
  "difficulty": "easy",
  "seed": 12345
}
```

字段说明：

- `scenario` 必填，取值为 `cooking`、`fire_safety`、`garbage_sorting`。
- `difficulty` 必填，取值为 `easy`、`medium`、`hard`。
- `seed` 可选；不传时由系统随机生成。

返回重点字段：

- `game_id`：本局 UUID。
- `seed`：本局随机种子。
- `game_file`：生成的 `.json` 文件路径。
- `initialRoom`：初始房间。
- `initial_obs`：初始房间中文描述。
- `targets` / `objectiveSummary`：目标摘要。
- `map`：地图节点和连线。
- `admissibleCommands`：当前建议命令。

### 3.5 `GET /api/game/<id>`

获取当前游戏状态。

返回重点字段：

- `response`：当前房间描述，不默认暴露下一步具体操作。
- `logMessage`：命令日志文本；无命令时通常等同于 `response`。
- `currentRoom` / `currentRoomId`：当前位置。
- `inventory`：背包中文物品名。
- `progress`：完成数、分数、失误数、多步骤进度。
- `targets`：目标列表，包含 `currentStep` 和 `steps` 数据，供提示按钮使用。
- `map`：地图。
- `done`：是否完成全部目标。

### 3.6 `GET /api/game/<id>/map`

获取地图结构。

返回：

- `rooms` / `nodes`：房间节点。
- `connections` / `edges`：房间连线。

房间字段包括：

- `id`
- `name`
- `x` / `y`
- `current`
- `visited`
- `targetCount`

### 3.7 `POST /api/game/<id>/command`

执行命令。

请求体：

```json
{
  "command": "查看背包"
}
```

返回字段与 `GET /api/game/<id>` 类似，额外关注：

- `lastActionResult.ok`：本次操作是否成功。
- `lastActionResult.action`：动作类别，如查看、移动、拾取、烹饪步骤。
- `lastActionResult.scoreDelta`：得分变化。
- `logMessage`：本次命令日志，只显示本次操作结果，不自动暴露下一步。
- `teachingTip`：下一步提示文本，前端默认隐藏，仅点击提示按钮后显示。

## 4. 真实 TextWorld 生成流程

### 4.1 随机世界元数据

`create_session()` 调用 `build_world_metadata()` 生成世界元数据：

- 根据场景选择房间库。
- 根据难度决定房间数和目标数。
- 根据 seed 随机选择目标。
- 随机确定起始房间。
- 生成地图连接关系。
- 将目标物品分配到房间。

### 4.2 GameMaker 构造游戏

后端使用 TextWorld `GameMaker`：

1. `maker.new_room()` 创建房间。
2. `maker.connect()` 创建方向连接。
3. `maker.set_player()` 设置玩家初始位置。
4. `maker.new(type="o", name=...)` 创建可交互对象。
5. 按场景创建 Quest 条件。

三类 Quest 设计：

- 烹制菜品：真实 TextWorld 层面以收集菜品所需食材为基础 Quest。
- 防火隐患：以拾取/处理隐患对象作为基础 Quest。
- 垃圾分类：以把垃圾对象放入对应垃圾桶作为基础 Quest。

### 4.3 保存和启动环境

生成流程：

```text
GameMaker.build()
Game.save(games/generated/<game_id>.json)
textworld.start(<game_file>, request_infos=EnvInfos(...))
env.reset()
```

`EnvInfos` 请求：

- `admissible_commands`
- `facts`
- `inventory`
- `location`
- `score`
- `moves`
- `objective`
- `max_score`
- `policy_commands`
- `intermediate_reward`
- `last_action`

命令执行：

```text
env.step(engine_command)
```

执行后后端读取新状态中的反馈、分数、facts、背包等信息，并包装为中文结构化响应。

## 5. 随机生成机制

### 5.1 seed

- 用户不传 `seed` 时，后端使用 `random.SystemRandom()` 生成随机 seed。
- 用户传入相同 `seed`、相同场景和难度时，可以复现目标选择和地图布局。

### 5.2 game_id

- 每局生成唯一 `game_id`。
- 对应文件保存为 `games/generated/<game_id>.json`。
- 后端内存 `game_sessions[game_id]` 保存环境对象和进度状态。

### 5.3 房间与地图

各场景有独立房间库，例如：

- 烹制菜品：厨房、储物间、冰箱区、餐厅。
- 防火隐患：客厅、厨房、卧室、阳台。
- 垃圾分类：家中、厨房、小区投放点、花园。

难度决定房间数量：

- easy：2 个房间。
- medium：3 个房间。
- hard：4 个房间。

连接模式使用预定义结构，保证地图连通。

### 5.4 目标与物品位置

目标会随机选择并分配到房间：

- cooking：从 20+ 菜品池中选取目标菜品，并把食材放入 TextWorld 房间。
- fire_safety：从 20+ 火灾隐患池中选取隐患目标。
- garbage_sorting：从 20+ 垃圾池中选取垃圾目标，并在房间中放置对应垃圾桶。

## 6. 三类场景

### 6.1 烹制菜品

目标：收集食材并按具体菜品步骤完成烹制。

示例流程：

- 煎鸡蛋：拿齐鸡蛋、油、盐 → 打散鸡蛋 → 热锅 → 倒油 → 下鸡蛋 → 翻面煎熟 → 盛出煎鸡蛋。
- 番茄炒蛋：拿齐番茄、鸡蛋、油、盐 → 切番茄 → 打散鸡蛋 → 热锅 → 倒油 → 下番茄、鸡蛋 → 翻炒 → 加盐调味 → 装盘。
- 青菜汤：拿齐青菜、水、盐 → 锅中加水 → 烧开清水 → 下青菜 → 调味 → 盛出。

烹饪多步骤由项目逻辑校验顺序，真实 TextWorld 负责底层食材收集和环境状态。

### 6.2 防火隐患

目标：识别并按步骤处理安全隐患。

示例：

- 观察插线板。
- 关闭相关电器。
- 拔掉多余插头。
- 整理线路。
- 确认隐患解除。

### 6.3 垃圾分类

目标：判断垃圾类别，必要时预处理，然后投放到正确垃圾桶。

示例：

- 判断苹果核为厨余垃圾。
- 投放苹果核到厨余垃圾桶。
- 确认分类完成。

## 7. 20+ 目标池与难度目标数量

### 7.1 cooking

- 目标池：22 个菜品。
- easy：1 道菜。
- medium：2 道菜。
- hard：3 道菜。

### 7.2 fire_safety

- 目标池：20+ 个隐患。
- easy：3 个隐患。
- medium：5 个隐患。
- hard：8 个隐患。

### 7.3 garbage_sorting

- 目标池：20+ 件垃圾。
- easy：5 件垃圾。
- medium：10 件垃圾。
- hard：15 件垃圾。

## 8. 多步骤流程与进度字段

### 8.1 状态存储

后端在 session 中保存步骤状态：

- cooking：`cookingSteps[target_id]`
- fire_safety / garbage_sorting：`targetSteps[target_id]`

每个状态包含：

```json
{
  "index": 0,
  "completed": []
}
```

### 8.2 `progress.targetProgress`

每个目标有独立进度：

```json
{
  "currentStep": "collect",
  "currentStepName": "拿齐鸡蛋、油、盐",
  "completedSteps": [],
  "stepIndex": 0,
  "stepTotal": 7
}
```

前端默认目标区只展示：

```text
目标名 · 进行中 · 步骤 0/7
```

不直接展示 `currentStepName`，避免默认暴露答案。

### 8.3 `targets[].currentStep` 和 `targets[].steps`

后端仍返回：

- `currentStep`
- `steps`
- 每步 `id/name/tip`

这些数据用于“查看提示”按钮。默认不展示，用户点击后才显示具体下一步。

## 9. 中文命令映射与别名

命令处理分前端和后端两层。

### 9.1 前端映射

`templates/index.html` 中 `translateCommand()` 处理常见中文输入：

- 查看 / 查看房间 / 观察。
- 查看背包 / 背包 / 物品栏。
- 前往东边 / 去东边 / 东。
- 拿起、拿取、拾取、拿。
- 做、制作、完成菜品、提交菜品。
- 处理、修复、关闭、清理、移开、熄灭。
- 分类、投放。

### 9.2 后端映射

`app.py` 中 `translate_command()` 进一步处理：

- `look` / `inventory`。
- 方向移动。
- 拾取物品。
- 烹饪步骤命令。
- 防火隐患步骤命令。
- 垃圾分类步骤命令。

后端会把中文对象名映射到 TextWorld 英文对象名，例如：

- 番茄 → `tomato`
- 鸡蛋 → `egg`
- 清水 → `clean water`
- 苹果核 → `apple core`

### 9.3 步骤别名

每个多步骤动作包含一组中文命令别名。例如煎鸡蛋：

- 打散鸡蛋：打鸡蛋、打蛋、搅打鸡蛋。
- 倒油：倒油、倒食用油、下油。
- 翻面煎熟：翻面、煎熟、煎熟鸡蛋。

后端通过步骤 `commands` 集合识别别名，并校验执行顺序。

## 10. `logMessage` 命令日志机制

为避免房间面板和命令日志混用，后端响应包含两个文本字段：

- `response`：当前房间/状态描述，供主面板显示。
- `logMessage`：本次命令执行结果，供日志区域显示。

设计原则：

- “查看背包”空背包显示：`背包为空`。
- “查看背包”非空显示：`背包中有：清水、大米`。
- “查看房间”显示房间描述、出口、可见物品/目标。
- 移动、拾取、多步骤操作只显示本次操作结果。
- 成功日志不自动拼接“下一步”。
- 错误顺序时允许显示纠错提示，例如“当前应先完成：打散鸡蛋”。

## 11. 提示按钮机制

用户反馈不希望页面默认暴露答案，因此前端采用折叠提示：

- 默认 `#teachingTip` 为隐藏状态。
- 按钮文字为“查看提示”。
- 点击后显示具体下一步。
- 再次点击隐藏。
- 执行命令后自动隐藏，避免操作后自动暴露下一步。

前端关键函数：

- `setHintExpanded(expanded)`：控制展开/隐藏。
- `buildHintText(data)`：从 `targets[].currentStep` 和 `steps[].tip` 生成提示文本。
- `sendCommand()`：命令执行后调用 `setHintExpanded(false)`。

## 12. 前端 UI 结构

页面为单文件模板：`templates/index.html`。

主要区域：

- 开始页：项目标题和进入按钮。
- 设置页：场景选择、难度选择、生成按钮。
- 游戏页：
  - 顶部：场景标题、当前房间。
  - 主面板：房间描述、命令输入、指令指南、命令日志。
  - 侧边栏：目标进度、背包、下一步提示按钮。
  - 地图面板：房间节点、连线、访问状态、目标数量。

目标进度默认显示：

```text
目标名 · 进行中 · 步骤 0/7
```

不会显示具体下一步名称。

## 13. 测试与验证方法

### 13.1 Python 语法检查

```powershell
python -m py_compile app.py test_api.py
```

### 13.2 启动服务

```powershell
python app.py
```

打开：

```text
http://127.0.0.1:5003/
```

### 13.3 引擎检查

```text
http://127.0.0.1:5003/api/engine
```

确认：

- `available=true`
- `engine=textworld-json`
- `error=null`

### 13.4 接口冒烟测试

```powershell
python test_api.py
```

### 13.5 手动功能验证

建议验证：

1. 生成 cooking/easy。
2. 默认房间描述和目标区不显示具体下一步。
3. 点击“查看提示”后显示当前目标下一步。
4. 查看背包：空背包显示“背包为空”。
5. 拾取物品后查看背包，显示实际物品。
6. 按步骤完成一个 cooking 目标。
7. 故意跳步，确认中文顺序错误提示存在。
8. 生成 fire_safety/easy 和 garbage_sorting/easy，确认 look 和基础步骤正常。

### 13.6 前端 JS 语法检查

可抽取 `<script>` 内容后使用 Node 检查：

```powershell
node --check <抽取出的脚本文件.js>
```

项目当前没有独立前端构建系统，因此无需 `npm install`。

## 14. 已知限制

1. **会话保存在内存中**
   - `game_sessions` 是进程内字典。
   - 服务重启后旧 `game_id` 会失效。

2. **生成文件会累积**
   - 每局生成 `games/generated/<game_id>.json`。
   - 需要定期清理旧文件。

3. **当前不使用 `.z8`**
   - Windows 上当前采用 `.json` Environment。
   - `.z8` / Inform / Z-machine 需要额外环境。

4. **未接入数据库和用户系统**
   - 当前适合教学演示和单机/小规模运行。
   - 不适合直接作为多用户生产系统。

5. **前端是单文件模板**
   - 易于部署和演示。
   - 若功能继续增多，建议拆分为组件化前端。

6. **控制台中文编码**
   - PowerShell 直接打印中文可能受编码影响。
   - 浏览器和 API 返回通常正常。

## 15. 后续优化建议

1. **持久化会话**
   - 将 `game_sessions` 存入 Redis、SQLite 或数据库。
   - 支持服务重启恢复。

2. **自动清理生成文件**
   - 增加定时任务清理 `games/generated/`。
   - 可按时间或数量保留。

3. **更完整的自动化测试**
   - 增加 Flask API 单元测试。
   - 增加 cooking/fire/garbage 多步骤回归测试。
   - 增加前端交互端到端测试。

4. **前端工程化**
   - 使用 Vue/React/Svelte 等框架拆分组件。
   - 引入静态类型和构建检查。

5. **更丰富的教学反馈**
   - 根据错误次数动态调整提示粒度。
   - 支持知识点总结和完成后的复盘。

6. **部署容器化**
   - 编写 Dockerfile 和 compose 文件。
   - 固定 Python/TextWorld 版本，降低环境差异。

7. **多语言与无障碍支持**
   - 增加英文界面或双语模式。
   - 优化键盘导航和 ARIA 文案。
