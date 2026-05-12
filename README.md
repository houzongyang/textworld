# 生活技能教学 TextWorld Web 游戏

这是一个浏览器 Web UI + Flask 后端的生活技能教学文字冒险游戏。当前版本接入真实 TextWorld 1.7.0 `.json` Environment：游戏世界由 TextWorld 生成，玩家命令通过真实 TextWorld environment 执行。

项目不再使用模拟 fallback。如果真实 TextWorld 引擎不可用，后端会返回明确错误，而不是切换到模拟逻辑。

## 文档

- [部署文档](docs/deployment.md)? 部署文档，覆盖环境要求、安装步骤、启动方式、引擎检查、常见问题和生成文件清理建议。
- [技术文档](docs/technical.md)? 详细技术文档，覆盖系统架构、API、TextWorld 生成流程、随机机制、多步骤流程、命令日志和提示按钮机制。

## 场景与难度

- `cooking`：烹制菜品，低难度 2 个房间 / 1 道菜，中难度 3 个房间 / 2 道菜，高难度 4 个房间 / 3 道菜。
- `fire_safety`：防患火灾隐患，低难度 2 个房间 / 3 个隐患，中难度 3 个房间 / 5 个隐患，高难度 4 个房间 / 8 个隐患。
- `garbage_sorting`：垃圾分类，低难度 2 个房间 / 5 件垃圾，中难度 3 个房间 / 10 件垃圾，高难度 4 个房间 / 15 件垃圾。

## 随机生成

每次调用 `POST /api/generate` 都会生成一局新的真实 TextWorld 游戏：

- 新的 `game_id` 和 `seed`。
- 新的游戏文件：`games/generated/<game_id>.json`。
- 房间、起始位置、地图连接、目标列表、物品/危险源/垃圾位置都会按难度约束随机生成。
- 返回给前端的地图、目标、进度和中文命令建议都与本局随机世界一致。
- 如需复现某一局，可在生成接口中传入相同 `seed`。

## 运行方式

```bash
python app.py
```

启动后在浏览器打开：`http://127.0.0.1:5003/`

## 真实 TextWorld 引擎

- 当前使用真实 TextWorld 1.7.0 `.json` Environment。
- `/api/engine` 可查看引擎状态，正常情况下返回 `available=true`、`engine=textworld-json`。
- `/api/generate` 负责随机生成并加载新的真实 TextWorld 游戏文件。
- `/api/game/<id>/command` 负责执行中文命令映射后的真实 TextWorld 动作。
- 不再使用模拟 fallback；TextWorld 未安装或不可用时会返回错误。

如果必须使用 `.z8`、Inform 或 Z-machine 文件，需要额外配置 Inform7，或使用 Linux / WSL / Docker 等支持环境。

## API

- `GET /api/engine`：查看真实 TextWorld 引擎是否可用。
- `GET /api/scenarios`：获取结构化场景、难度和教学配置。
- `POST /api/generate`：传入 `scenario` 和 `difficulty`，随机生成游戏并返回 `game_id`、`seed`、`game_file`、初始状态、目标摘要和地图。
- `GET /api/game/<id>`：获取当前游戏状态。
- `GET /api/game/<id>/map`：获取地图节点和连线，包含 `x/y/current/visited/targetCount` 等字段。
- `POST /api/game/<id>/command`：执行命令，返回 `response/currentRoom/inventory/progress/lastActionResult/teachingTip/done/map` 等结构化字段。

## 中文命令示例

Web UI 面向用户展示中文命令，并由前端/后端映射到真实 TextWorld 可执行动作。常用示例：

- 查看房间：查看当前房间描述、可见物品和可行动方向。
- 查看背包：查看已经拿到的道具或物品。
- 前往东边：移动到东边相邻房间，也可使用“前往西边 / 前往南边 / 前往北边”。
- 拿番茄：拾取当前房间中的番茄，也支持“拿起番茄”“拾取番茄”。
- 处理超负荷插线板：在防患火灾隐患场景中处理指定隐患。
- 投放苹果核到厨余垃圾：在垃圾分类场景中把垃圾投放到正确类别。

## 验证

可先检查 Python 文件语法：

```bash
python -m py_compile app.py test_api.py
```

启动服务后，也可以运行接口冒烟测试：

```bash
python test_api.py
```
