#!/usr/bin/env python3
"""修改论文：
1. 扩充3.3节三个应用场景的具体描述
2. 将第4章截图替换为文字代码块
3. 插入游戏运行截图（图4-2/4-3/4-4素材）
"""
import re, sys, os, base64, struct, zlib
sys.stdout.reconfigure(encoding='utf-8')

UNPACKED = r'E:\360MoveData\Users\ASUS\Desktop\textworld\论文_unpacked'
DOC_XML = os.path.join(UNPACKED, 'word', 'document.xml')

with open(DOC_XML, encoding='utf-8') as f:
    xml = f.read()

def make_normal_para(text, style='1111', rsid='00AA1234'):
    """生成正文段落XML"""
    lines = text.split('\n')
    runs = []
    for line in lines:
        if line:
            runs.append(f'      <w:r><w:t xml:space="preserve">{line}</w:t></w:r>')
    runs_xml = '\n'.join(runs)
    return f'''    <w:p w14:paraId="{rsid}" w14:textId="77777777" w:rsidR="00AA1234" w:rsidRDefault="00AA1234">
      <w:pPr>
        <w:pStyle w:val="{style}"/>
      </w:pPr>
{runs_xml}
    </w:p>'''

def make_code_para(code_text, rsid='00BB5678'):
    """生成代码段落XML（使用等宽字体）"""
    lines = code_text.strip().split('\n')
    para_list = []
    for line in lines:
        escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        para_list.append(f'''    <w:p w14:paraId="{rsid}" w14:textId="77777777" w:rsidR="00CC9012" w:rsidRDefault="00CC9012">
      <w:pPr>
        <w:pStyle w:val="1111"/>
        <w:ind w:left="240" w:firstLine="0"/>
        <w:rPr>
          <w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>
          <w:sz w:val="18"/>
          <w:szCs w:val="18"/>
        </w:rPr>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>
          <w:sz w:val="18"/>
          <w:szCs w:val="18"/>
        </w:rPr>
        <w:t xml:space="preserve">{escaped}</w:t>
      </w:r>
    </w:p>''')
    return '\n'.join(para_list)

# ================================================================
# 1. 扩充 3.3.1 菜谱做菜游戏设计
# ================================================================
NEW_331_CONTENT = """菜谱做菜这个游戏主题的主要目的是帮助用户去学习基础的烹饪流程以及厨房操作方面的相关知识。该主题通过模拟一个厨房环境的方式，让玩家按照菜谱所提出的要求去依次完成取材、准备、烹饪以及装盘等一系列的操作。游戏当中所涉及到的关键对象主要包括食材、厨具、容器以及烹饪设备等几个类别。在进行具体设计的过程当中，菜谱做菜主题重点体现了以下几个方面的特征：

第一，强调操作的顺序性。烹饪步骤必须按照合理的顺序执行，例如玩家需要先拿齐食材，再进行清洗、切配，最后加热出锅。如果顺序错误，系统会提示当前应完成的步骤，引导玩家纠正操作。

第二，强调工具与食材的匹配性。不同菜品或不同步骤需要用到不同的工具（如锅、刀、盘子等），系统会根据当前步骤的要求自动校验操作合法性。

第三，强调结果导向性。每道菜品设有完整的操作链，玩家必须按顺序完成所有步骤后才能"出锅"成功。系统在每个步骤完成时给出正向反馈，错误时给出纠正提示。

在具体实现方面，系统内置了22种常见菜品，涵盖炒菜（如番茄炒蛋、土豆丝）、汤类（如青菜汤、紫菜蛋花汤）、主食（如米饭、煮面条）和凉拌（如凉拌黄瓜）等多个类别。每次游戏从中随机选择若干道菜品作为目标。以"番茄炒蛋"为例，其完整操作链如下："""

NEW_331_STEPS = """（1）拿齐番茄、鸡蛋、食用油和盐；（2）洗番茄；（3）切番茄；（4）打鸡蛋；（5）热锅倒油；（6）先炒鸡蛋；（7）加入番茄；（8）加盐调味；（9）出锅番茄炒蛋。"""

NEW_331_EXTRA = """玩家每步输入对应的中文指令（如"洗番茄"、"热锅倒油"），系统判断该指令是否与当前步骤匹配。操作正确时给出"已完成：XXX"的反馈；操作顺序错误时提示"顺序不对，请先完成：XXX"；食材未备齐时提示缺少的食材名称。不同难度等级通过增加目标菜品数量（简单1道、普通2道、困难3道）来体现复杂度差异，游戏场景包含厨房、储物间、冰箱区、餐厅等多个房间，玩家需要在不同房间之间移动以收集分散放置的食材。"""

NEW_332_CONTENT = """防范火灾这个游戏主题的主要目的是普及消防安全方面的基础知识以及基本的应急处理能力。玩家需要在特定的场景当中去识别出潜在的火灾隐患，并且采取正确的操作来进行预防或者应对。该主题具有比较强的教育意义和现实价值，它的设计重点主要包括以下几个方面的内容：

第一，突出风险识别这一环节。玩家需要根据场景当中所呈现出来的信息去判断哪些行为或者哪些状态存在火灾方面的风险，例如超负荷插线板、燃气阀门未关等。

第二，突出正确的应对方式。面对已经发生或者即将发生的危险情况，玩家需要按照系统预设的步骤逐一完成处理操作。例如，针对"超负荷插线板"这一隐患，完整处理步骤为：观察插线板 → 关闭相关电器 → 拔掉多余插头 → 整理线路 → 确认隐患解除；针对"燃气阀门未关"，步骤为：观察灶台 → 关闭燃气阀门 → 打开窗户通风 → 不触碰明火电源 → 确认安全。

第三，突出错误操作的警示作用。如果玩家跳步或采取了不符合当前进度的操作，系统会提示"顺序不对，请先完成：XXX"，帮助玩家理解规范处置流程。

在具体实现方面，系统内置了23种常见火灾隐患，分布在客厅、厨房、卧室、阳台等不同房间。每次游戏随机从中抽取若干个隐患作为本局目标（简单3个、普通5个、困难8个）。玩家在各房间内移动并执行对应的中文处理指令，例如"观察超负荷插线板"、"关闭燃气阀门"等。每个隐患均关联详细的知识讲解，在处理完成后系统会显示该隐患的风险说明，帮助玩家形成安全意识。"""

NEW_333_CONTENT = """垃圾分类这个游戏主题的主要目的是帮助用户掌握常见垃圾的类别划分以及相应的投放规则。玩家需要在给定的场景当中去识别出不同的垃圾物品，并且把它们正确地放入对应的垃圾桶当中。可以设置的垃圾类型主要包括可回收物、有害垃圾、厨余垃圾以及其他垃圾这几个大类。该主题在设计方面主要强调以下几个方面的能力要求：

第一，物品识别能力。用户需要根据物品本身的性质以及用途判断其类别，例如旧报纸属于可回收物、废电池属于有害垃圾、苹果核属于厨余垃圾、污纸巾属于其他垃圾。

第二，规则匹配能力。玩家需要将具体物品与正确的垃圾桶类型对应，系统会根据正确分类给出知识点讲解。

第三，预处理意识。部分复合包装物品（如塑料瓶、快递纸箱、奶茶杯等）投放前需要先进行预处理，例如清空压扁塑料瓶、压扁快递纸箱等。系统会在判断和投放步骤之间额外插入预处理步骤，引导玩家建立正确的分类习惯。

在具体实现方面，系统内置了24种常见垃圾物品，覆盖四大分类。每轮游戏操作流程如下：（1）拿起目标垃圾物品；（2）如有需要，先完成预处理（如"清空压扁塑料瓶"）；（3）判断所属类别（如"判断为可回收物"）；（4）投放到对应垃圾桶（如"投放到可回收物桶"）。例如，对于"旧报纸"的完整操作为：拿起旧报纸 → 判断为可回收物 → 投放到可回收物桶；对于"塑料瓶"则需要额外的预处理步骤：拿起塑料瓶 → 清空压扁塑料瓶 → 判断为可回收物 → 投放到可回收物桶。不同难度通过增加垃圾物品数量（简单5件、普通10件、困难15件）来体现难度差异，游戏场景包含家中、厨房、小区投放点、花园等多个房间，玩家需要在各房间收集垃圾并前往小区投放点完成分类。"""

# 找到3.3.1正文内容区域（标题后到3.3.2标题前）
idx_331_title = xml.find('菜谱做菜游戏设计', 80000)
after_title_331 = xml.find('</w:p>', idx_331_title) + 6
idx_332_title = xml.find('防范火灾游戏设计', 80000)
p_332_start = xml.rfind('<w:p ', 0, idx_332_title)

# 3.3.1 原始正文
old_331_body = xml[after_title_331:p_332_start]

# 构建新的3.3.1正文
new_331_body = (
    make_normal_para(NEW_331_CONTENT) + '\n' +
    make_normal_para(NEW_331_STEPS) + '\n' +
    make_normal_para(NEW_331_EXTRA) + '\n'
)

xml = xml[:after_title_331] + new_331_body + xml[p_332_start:]
print("3.3.1 替换完成")

# 找到3.3.2正文内容区域
# 重新搜索（xml已变化）
idx_332_title = xml.find('防范火灾游戏设计', 80000)
after_title_332 = xml.find('</w:p>', idx_332_title) + 6
idx_333_title = xml.find('垃圾分类游戏设计', 240000)
p_333_start = xml.rfind('<w:p ', 0, idx_333_title)

old_332_body = xml[after_title_332:p_333_start]
new_332_body = make_normal_para(NEW_332_CONTENT) + '\n'
xml = xml[:after_title_332] + new_332_body + xml[p_333_start:]
print("3.3.2 替换完成")

# 找到3.3.3正文内容区域
idx_333_title = xml.find('垃圾分类游戏设计', 240000)
after_title_333 = xml.find('</w:p>', idx_333_title) + 6
idx_34_title = xml.find('难度分级机制', 244000)
p_34_start = xml.rfind('<w:p ', 0, idx_34_title)

old_333_body = xml[after_title_333:p_34_start]
new_333_body = make_normal_para(NEW_333_CONTENT) + '\n'
xml = xml[:after_title_333] + new_333_body + xml[p_34_start:]
print("3.3.3 替换完成")

# ================================================================
# 2. 将截图段落 + 说明行替换为文字代码块
# ================================================================

# 定义每个图对应的代码内容
CODE_BLOCKS = {
    '图4-1 Flask应用初始化': '''from flask import Flask, jsonify, render_template, request
import os, subprocess, json, uuid

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.secret_key = "life-skills-textworld-demo"''',

    '图4-2 返回前端': '''@app.route("/")
def index():
    return render_template("index.html")''',

    '图4-3 游戏场景配置': '''GAME_SCENARIOS = {
    "cooking": {
        "id": "cooking", "name": "烹制菜品",
        "description": "收集食材并完成目标菜品。",
        "difficulties": {
            "easy":   {"rooms": 2, "targets": 1},
            "medium": {"rooms": 3, "targets": 2},
            "hard":   {"rooms": 4, "targets": 3}
        }
    },
    "fire_safety": {
        "id": "fire_safety", "name": "防患火灾隐患",
        "description": "巡视房间并处理安全隐患。",
        "difficulties": {
            "easy":   {"rooms": 2, "targets": 3},
            "medium": {"rooms": 3, "targets": 5},
            "hard":   {"rooms": 4, "targets": 8}
        }
    },
    "garbage_sorting": {
        "id": "garbage_sorting", "name": "垃圾分类",
        "description": "拾取垃圾并投放到正确类别。",
        "difficulties": {
            "easy":   {"rooms": 2, "targets": 5},
            "medium": {"rooms": 3, "targets": 10},
            "hard":   {"rooms": 4, "targets": 15}
        }
    },
}''',

    '图4-4 游戏会话与状态管理': '''# 游戏会话字典：保存游戏基本信息
game_sessions: dict[str, dict] = {}

# 示例会话结构：
session = {
    "scenario": scenario_id,      # 游戏主题
    "difficulty": difficulty,      # 难度等级
    "engine": "textworld-json",    # 引擎类型
    "game_file": str(game_file),   # 游戏文件路径
    "env": env,                    # TextWorld 环境对象
    "tw_state": tw_state,          # 当前游戏状态
    "currentRoom": world["startRoom"],
    "visitedRooms": {world["startRoom"]},
    "completedTargetIds": set(),
    "mistakes": 0,
    "done": False,
}''',

    '图4-5 生成游戏编号': '''import uuid

game_id = str(uuid.uuid4())
# 示例：'a3f2c1e0-4b5d-4e6f-8a9b-0c1d2e3f4a5b'
game_file = GENERATED_GAMES_DIR / f"{game_id}.json"''',

    '图4-6 场景列表获取接口': '''@app.get("/api/scenarios")
def get_scenarios():
    scenarios = deepcopy(GAME_SCENARIOS)
    labels = {"easy": "低难度", "medium": "中难度", "hard": "高难度"}
    for scenario in scenarios.values():
        for key, config in scenario["difficulties"].items():
            config["id"] = key
            config["name"] = labels[key]
    return jsonify(scenarios)''',

    '图4-7 接口开始部分': '''@app.post("/api/generate")
def generate_game():
    data = request.get_json(silent=True) or {}
    scenario_id = data.get("scenario")
    difficulty = data.get("difficulty")
    # 参数校验
    if scenario_id not in GAME_SCENARIOS:
        return jsonify({"error": "无效场景"}), 400
    if difficulty not in GAME_SCENARIOS[scenario_id]["difficulties"]:
        return jsonify({"error": "无效难度"}), 400''',

    '图4-8 生成游戏命令': '''# 菜谱做菜：调用 TextWorld GameMaker API 生成 cooking 类型游戏
# 防患火灾 / 垃圾分类：调用 TextWorld GameMaker API 生成 simple 类型游戏
game_file = create_textworld_game_file(scenario_id, difficulty, world, game_id)

# 核心生成函数片段：
def create_textworld_game_file(scenario_id, difficulty, world, game_id):
    maker = GameMaker()
    room_entities = {room["id"]: maker.new_room(room["name"])
                     for room in world["rooms"]}
    maker.set_player(room_entities[world["startRoom"]])
    # ... 添加连接、物品、任务 ...
    game = maker.build()
    game_file = GENERATED_GAMES_DIR / f"{game_id}.json"
    game.save(str(game_file))
    return game_file''',

    '图4-9 执行外部命令': '''result = subprocess.run(
    tw_make_command,
    capture_output=True,   # 捕获 stdout/stderr
    text=True,             # 以字符串形式返回输出
    cwd=work_dir           # 指定命令执行目录
)''',

    '图4-10 输出错误信息': '''if result.returncode != 0:
    print("游戏生成失败:", result.stderr)
    return jsonify({
        "error": "游戏生成失败",
        "detail": result.stderr
    }), 500''',

    '图4-11 返回信息': '''return jsonify({
    "game_id": game_id,
    "scenario": scenario_id,
    "difficulty": difficulty,
    "config": GAME_SCENARIOS[scenario_id]["difficulties"][difficulty],
    "engine": session["engine"],
    "game_file": session["game_file"],
    "seed": session["seed"],
    "initial_obs": describe_room(session, ...),
    "targets": target_summary(session),
    "map": build_map(session),
    "admissibleCommands": visible_command_suggestions(session),
})''',

    '图4-12 游戏初始化': '''def make_env(game_file):
    infos = EnvInfos(
        admissible_commands=True,
        facts=True,
        inventory=True,
        location=True,
        score=True,
        objective=True,
    )
    env = textworld.start(str(game_file), request_infos=infos)
    state = env.reset()   # 重置游戏并返回初始观察信息
    return env, state''',

    '图4-13 捕捉错误': '''try:
    env, tw_state = make_env(game_file)
    game_sessions[game_id] = session
except Exception as exc:
    # 捕获初始化异常，避免 Flask 服务崩溃
    return jsonify({
        "error": "TextWorld 引擎不可用",
        "detail": str(exc)
    }), 500''',

    '图4-14 游戏信息获取接口': '''@app.get("/api/game/<game_id>")
def get_game(game_id):
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "游戏不存在或已过期"}), 404
    return jsonify(response_payload(
        session,
        describe_room(session),
        teaching_tip="继续探索并完成所有目标。"
    ))''',

    '图4-15 游戏编号判断': '''@app.get("/api/game/<game_id>/map")
def get_game_map(game_id):
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({
            "error": "游戏不存在或已过期",
            "rooms": [],
            "connections": []
        }), 404
    return jsonify(build_map(session))''',

    '图4-16 地图生成': '''def build_map(session):
    completed = completed_target_ids(session)
    rooms = []
    for room in session["world"]["rooms"]:
        target_count = sum(
            1 for item in room.get("items", [])
            if item["id"] not in completed
        )
        rooms.append({
            "id": room["id"],
            "name": room["name"],
            "x": room["x"], "y": room["y"],
            "current": room["id"] == session["currentRoom"],
            "visited": room["id"] in session["visitedRooms"],
            "targetCount": target_count
        })
    return {
        "rooms": rooms,
        "connections": session["world"]["connections"]
    }''',

    '图4-17 接口代码': '''@app.post("/api/game/<game_id>/command")
def game_command(game_id):
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "游戏不存在或已过期"}), 404
    command = (request.get_json(silent=True) or {}).get("command", "")
    if not command.strip():
        return jsonify({"error": "缺少 command 参数"}), 400''',

    '图4-18 检查初始化': '''tw_command, action = translate_command(session, command)
# 检查游戏状态是否已完成初始化
if action in SCENE_STEP_ACTIONS:
    result = handle_target_step(session, tw_command)
    response = describe_room(session, result.pop("feedback", ""))
    return jsonify(response_payload(session, response, result, ...))
commands = command_sequence_for(session, tw_command, action)''',

    '图4-19 obs分类处理': '''def clean_engine_feedback(feedback):
    text = str(feedback or "").strip()
    if not text or "To get text observation" in text:
        return ""
    if text == "Invalid command.":
        return "这个中文指令暂时无法执行，请换一种说法或先查看房间。"
    # 对有效的中文反馈直接返回
    if any(text.startswith(prefix)
           for prefix in ("食材", "顺序", "已完成", "番茄炒蛋")):
        return text
    return ""''',

    '图4-20 异常处理': '''try:
    for engine_command in commands:
        tw_state, score, done = session["env"].step(engine_command)
        session["tw_state"] = tw_state
        feedback = getattr(tw_state, "feedback", "") or ""
        if feedback.strip() == "Invalid command.":
            break
except Exception as exc:
    return jsonify({
        "error": "真实引擎命令执行失败",
        "detail": str(exc)
    }), 500''',

    '图4-21 加载游戏': '''env = textworld.start(str(game_file), request_infos=infos)
state = env.reset()  # 重置游戏环境，获取初始观察

# 执行命令示例：
obs, score, done = env.step("take tomato")
# obs：游戏返回的文字反馈
# score：当前累计得分
# done：任务是否已完成''',

    '图4-22 系统后端程序': '''if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    app.run(
        host="0.0.0.0",   # 允许外部地址访问
        port=5003,         # 服务运行端口
        debug=True         # 开启调试模式
    )
# 启动命令：python3 app.py
# 访问地址：http://127.0.0.1:5003''',

    '图4-24 访问Windows磁盘文件': '''# WSL Ubuntu 环境中通过 /mnt/c/... 路径访问 Windows 磁盘文件
TW_MAKE_PATH = "/mnt/c/Users/user/AppData/Local/Programs/Python/Python311/Scripts/tw-make"

def find_tw_make():
    return shutil.which("tw-make") or str(
        next(Path(sys.prefix, "Scripts").glob("tw-make*"), "")
    ) or None''',

    '图4-25 game_states字典': '''# game_sessions 字典保存每个游戏的完整会话（含 TextWorld 环境对象）
game_sessions: dict[str, dict] = {}

# 后续命令执行时，根据 game_id 找到对应的 env 对象继续执行：
session = game_sessions.get(game_id)
env = session["env"]
tw_state, score, done = env.step(command)''',

    '图4-26 判断命令执行结果': '''# 检查 subprocess.run() 的返回码
result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
if result.returncode != 0:
    print("生成失败 stdout:", result.stdout)
    print("生成失败 stderr:", result.stderr)
    return jsonify({
        "error": "游戏生成失败",
        "detail": result.stderr
    }), 500''',
}

# 找到第4章开始位置
ch4_start = xml.find('第4章 系统实现', 260000)
print(f"第4章开始位置: {ch4_start}")

# 找出所有图说明段落及其前面的drawing段落，一并替换
para_pattern = re.compile(r'<w:p [^>]+>.*?</w:p>', re.DOTALL)

# 收集所有图说明段落
captions_to_replace = []
for m in para_pattern.finditer(xml, ch4_start):
    text = ''.join(re.findall(r'<w:t[^>]*>([^<]+)</w:t>', m.group()))
    text = text.strip()
    if re.match(r'^图4-\d+', text) and len(text) < 80:
        # 找到前一个段落（通常是drawing段落）
        prev_matches = list(para_pattern.finditer(xml, max(ch4_start, m.start()-3000), m.start()))
        if prev_matches:
            last_prev = prev_matches[-1]
            has_drawing = '<w:drawing' in last_prev.group() or '<v:shape' in last_prev.group()
            if has_drawing:
                captions_to_replace.append((last_prev.start(), m.end(), text))
            else:
                captions_to_replace.append((m.start(), m.end(), text))
        else:
            captions_to_replace.append((m.start(), m.end(), text))

print(f"找到 {len(captions_to_replace)} 个图说明（含前置drawing）")

# 从后往前替换，避免位置偏移
for start, end, caption_text in reversed(captions_to_replace):
    if caption_text in CODE_BLOCKS:
        code = CODE_BLOCKS[caption_text]
        # 特殊处理：图4-23是要插入游戏截图的，保留说明行但不替换为代码
        if caption_text == '图4-23 浏览器界面':
            # 保留原样，后续处理截图
            continue
        replacement = make_code_para(code) + '\n'
        xml = xml[:start] + replacement + xml[end:]
        print(f"  替换: {caption_text}")
    else:
        print(f"  跳过（无代码块）: {caption_text}")

print("第4章截图替换完成")

# ================================================================
# 写回 XML
# ================================================================
with open(DOC_XML, 'w', encoding='utf-8') as f:
    f.write(xml)
print("document.xml 已保存")
