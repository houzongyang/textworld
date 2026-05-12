# 部署文档

本文档用于部署和运行“生活技能教学 TextWorld Web 游戏”。项目采用 Flask Web 服务作为后端，浏览器页面作为前端，后端通过真实 TextWorld `.json` Environment 生成并执行游戏。

## 1. 环境要求

### 操作系统

- 推荐：Windows 10/11。
- 也可在 Linux、macOS、WSL 或 Docker 中运行，但需要重新安装 Python 和 TextWorld 依赖。
- 当前项目在 Windows 环境下使用 TextWorld `.json` Environment，不依赖 `.z8` 文件运行。

### Python

- 推荐 Python 3.11 或 3.12。
- 项目目录中已有 `textworld_env/` 虚拟环境时，可优先复用该环境。
- 如需重新部署，建议创建独立虚拟环境，避免与系统 Python 包冲突。

### Python 依赖

核心依赖包括：

- `Flask`：提供 Web 页面和 REST API。
- `textworld`：生成和运行 TextWorld `.json` 游戏环境。
- TextWorld 依赖项：如 `numpy`、`networkx`、`tqdm`、`jericho` 等，通常由 `pip install textworld` 自动安装。

当前 README 中说明项目接入真实 TextWorld 1.7.0 `.json` Environment；部署时建议使用同一大版本，避免 TextWorld API 行为差异。

## 2. 安装步骤

### 2.1 进入项目目录

```powershell
cd E:\360MoveData\Users\ASUS\Desktop\textworld
```

### 2.2 创建虚拟环境（可选但推荐）

```powershell
python -m venv textworld_env
.\textworld_env\Scripts\Activate.ps1
```

如果 PowerShell 禁止执行脚本，可临时允许当前进程执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\textworld_env\Scripts\Activate.ps1
```

### 2.3 安装依赖

如果已有可用虚拟环境，可跳过此步。重新部署时执行：

```powershell
python -m pip install --upgrade pip
python -m pip install flask textworld
```

如安装 TextWorld 失败，请优先检查 Python 版本、编译工具链和网络源。Windows 上建议使用稳定 Python 版本，并避免过新的未适配版本。

## 3. 当前 Windows 运行方式说明

本项目当前使用真实 TextWorld `.json` Environment：

1. 后端使用 `GameMaker` 构造房间、物品、任务和 Quest。
2. 使用 `Game.save()` 将生成结果保存为 `games/generated/<game_id>.json`。
3. 使用 `textworld.start(<json 文件>, request_infos=EnvInfos(...))` 启动环境。
4. 玩家命令经中文映射后调用 `env.step(command)` 执行。

因此，当前 Windows 部署不需要 Inform7 或 Z-machine 即可运行 `.json` 游戏。

## 4. 启动服务

在项目根目录执行：

```powershell
python app.py
```

服务默认监听：

```text
http://127.0.0.1:5003/
```

浏览器打开该地址即可进入 Web UI。

## 5. 检查引擎状态

启动后访问：

```text
http://127.0.0.1:5003/api/engine
```

正常情况下应看到类似字段：

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

重点检查：

- `available=true`：说明 Python 可以导入 TextWorld。
- `engine=textworld-json`：说明项目当前运行模式为 `.json` Environment。
- `error=null`：说明导入阶段没有异常。

## 6. 常见启动问题和解决方案

### 6.1 `ModuleNotFoundError: No module named 'flask'`

原因：当前 Python 环境没有安装 Flask。

解决：

```powershell
python -m pip install flask
```

### 6.2 `ModuleNotFoundError: No module named 'textworld'`

原因：当前 Python 环境没有安装 TextWorld，或没有激活虚拟环境。

解决：

```powershell
.\textworld_env\Scripts\Activate.ps1
python -m pip install textworld
```

然后重新运行：

```powershell
python app.py
```

### 6.3 `/api/generate` 返回“真实 TextWorld 引擎不可用”

原因可能包括：

- TextWorld 未安装或导入失败。
- Python 环境与安装依赖的环境不是同一个。
- TextWorld 某些依赖未正确安装。

排查方式：

```powershell
python -c "import textworld; print(textworld.__version__)"
```

并访问 `/api/engine` 查看 `error` 字段。

### 6.4 端口 5003 被占用

现象：启动时报端口占用或无法绑定。

解决：

- 关闭占用 5003 的旧进程。
- 或修改 `app.py` 底部 `app.run(host="0.0.0.0", port=5003, debug=True)` 的端口。

### 6.5 PowerShell 中文显示乱码

本项目源码和接口返回使用 UTF-8。若 PowerShell 直接打印中文出现乱码，可尝试：

```powershell
$env:PYTHONIOENCODING='utf-8'
chcp 65001
```

浏览器页面和 JSON API 一般不受 PowerShell 控制台编码影响。

## 7. `.z8` / Inform / Z-machine 限制

当前项目使用 TextWorld `.json` Environment，不生成 `.z8` 文件，也不依赖 Inform7。

如果后续必须使用传统 `.z8` / Z-machine 文件，需要额外准备：

- Inform7 编译环境。
- TextWorld 对 Z-machine 的运行支持。
- 可能需要 Linux、WSL 或 Docker 环境以减少 Windows 兼容性问题。
- 需要重新设计生成与启动流程，例如从 `Game.save(.json)` 调整为 TextWorld 命令行或 Inform 编译链路。

建议当前交付继续使用 `.json` Environment，稳定性和部署成本更可控。

## 8. 生成文件清理建议

每次调用 `POST /api/generate` 都会生成一个文件：

```text
games/generated/<game_id>.json
```

这些文件用于当前游戏会话复现和 TextWorld 环境启动。长期演示或测试后可能积累较多文件。

建议：

- 开发调试期间可定期清理 `games/generated/` 下较旧的 `.json` 文件。
- 不要在服务正在运行且用户仍在游戏时删除当前会话对应的文件。
- 如需自动清理，可按最后修改时间保留最近 N 天或最近 N 个文件。
- 清理前确认不需要根据旧 `seed` / `game_id` 复现历史局。

PowerShell 示例：删除 7 天前生成文件：

```powershell
Get-ChildItem games\generated\*.json | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item
```

## 9. 部署后验证清单

部署完成后建议执行：

```powershell
python -m py_compile app.py test_api.py
python app.py
```

浏览器或接口检查：

1. 打开 `http://127.0.0.1:5003/`，首页正常显示。
2. 访问 `/api/engine`，确认 `available=true`。
3. 在页面选择任一场景和难度，生成游戏成功。
4. 输入“查看房间”“查看背包”，命令日志正常显示中文结果。
5. 点击“查看提示”按钮后才显示下一步提示，默认目标区不暴露具体答案。
