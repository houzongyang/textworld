#!/usr/bin/env python3
"""生活技能教学 TextWorld Web 游戏后端。

本服务只使用真实 TextWorld 环境：/api/generate 会生成或加载 TextWorld .json
游戏文件，/api/game/<id>/command 会调用 textworld.Environment.step 执行命令。
若 TextWorld 不可用会返回明确错误，不提供模拟 fallback。
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import random
import re
import shutil
import sys
import uuid

from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
GAMES_DIR = BASE_DIR / "games"
GAMES_DIR.mkdir(exist_ok=True)
GENERATED_GAMES_DIR = GAMES_DIR / "generated"
GENERATED_GAMES_DIR.mkdir(exist_ok=True)

try:
    import textworld
    from textworld import EnvInfos, GameMaker
    from textworld.generator.game import Event, Quest
except Exception as exc:  # pragma: no cover - surfaced through API.
    textworld = None
    EnvInfos = GameMaker = Event = Quest = None
    TEXTWORLD_IMPORT_ERROR = exc
else:
    TEXTWORLD_IMPORT_ERROR = None

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.secret_key = "life-skills-textworld-demo"


ROOM_LIBRARY = {
    "cooking": [
        {"id": "kitchen", "name": "厨房", "x": 0, "y": 0, "description": "灶台、锅具和调料都在这里。"},
        {"id": "pantry", "name": "储物间", "x": 1, "y": 0, "description": "货架上放着主食和干货。"},
        {"id": "fridge", "name": "冰箱区", "x": 0, "y": 1, "description": "冷藏食材需要在这里寻找。"},
        {"id": "dining", "name": "餐厅", "x": 1, "y": 1, "description": "完成菜品后可以在这里提交。"},
    ],
    "fire_safety": [
        {"id": "living_room", "name": "客厅", "x": 0, "y": 0, "description": "家人常活动的区域，电器较多。"},
        {"id": "kitchen", "name": "厨房", "x": 1, "y": 0, "description": "这里最容易出现明火和燃气风险。"},
        {"id": "bedroom", "name": "卧室", "x": 0, "y": 1, "description": "睡前需要检查插座和取暖设备。"},
        {"id": "balcony", "name": "阳台", "x": 1, "y": 1, "description": "杂物堆放可能阻碍逃生。"},
    ],
    "garbage_sorting": [
        {"id": "home", "name": "家中", "x": 0, "y": 0, "description": "日常垃圾散落在桌面和地上。"},
        {"id": "kitchen", "name": "厨房", "x": 1, "y": 0, "description": "厨余垃圾和包装物混在一起。"},
        {"id": "community", "name": "小区投放点", "x": 0, "y": 1, "description": "四类垃圾桶整齐摆放。"},
        {"id": "garden", "name": "花园", "x": 1, "y": 1, "description": "户外活动后也留下了一些垃圾。"},
    ],
}

CONNECTION_PATTERNS = {
    2: [("east", 0, 1)],
    3: [("east", 0, 1), ("south", 0, 2)],
    4: [("east", 0, 1), ("south", 0, 2), ("south", 1, 3), ("east", 2, 3)],
}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
DIRECTION_LABELS = {"north": "北", "south": "南", "east": "东", "west": "西"}
DIRECTION_ALIASES = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "北": "north", "南": "south", "东": "east", "西": "west",
    "北边": "north", "南边": "south", "东边": "east", "西边": "west",
    "向北": "north", "向南": "south", "向东": "east", "向西": "west",
}
LOOK_COMMANDS = {"look", "l", "查看", "观察", "查看房间", "查看当前房间"}
INVENTORY_COMMANDS = {"inventory", "inv", "i", "背包", "查看背包"}
MOVE_VERBS = {"go", "move", "walk", "去", "移动", "前往"}
TAKE_VERBS = {"take", "get", "pick", "拿", "拿起", "拾取", "捡", "捡起"}
COOK_VERBS = {"cook", "make", "prepare", "submit", "做", "制作", "提交", "完成"}
COOKING_STEP_VERBS = {"洗", "清洗", "切", "打", "搅打", "热", "倒", "炒", "加入", "加", "调味", "出锅", "盛出"}
FIX_VERBS = {"fix", "handle", "remove", "turn", "close", "clean", "处理", "修复", "关闭", "清理", "熄灭", "移开", "拔掉"}
SORT_VERBS = {"sort", "put", "throw", "drop", "insert", "分类", "投放", "丢", "扔", "放入"}
ACTION_LABELS = {
    "look": "查看",
    "inventory": "查看背包",
    "move": "移动",
    "take": "拾取",
    "cook": "做菜",
    "cook_collect": "备齐食材",
    "fix_hazard": "处理隐患",
    "sort": "垃圾分类",
    "help": "帮助",
    "textworld": "执行",
}

COOKING_DISHES = [
    {"id": "tomato_egg", "name": "????", "ingredients": ["tomato", "egg", "cooking oil", "salt"], "tip": "????????????????????????????????????????????"},
    {"id": "rice", "name": "??", "ingredients": ["rice", "clean water"], "tip": "??????????"},
    {"id": "vegetable_soup", "name": "???", "ingredients": ["green vegetable", "clean water", "salt"], "tip": "?????????????"},
    {"id": "potato_shreds", "name": "???", "ingredients": ["potato", "cooking oil", "salt"], "tip": "???????????????????"},
    {"id": "carrot_egg", "name": "?????", "ingredients": ["carrot", "egg", "cooking oil", "salt"], "tip": "???????????????????????"},
    {"id": "noodles", "name": "???", "ingredients": ["noodles", "clean water", "salt"], "tip": "?????????????????"},
    {"id": "egg_soup", "name": "???", "ingredients": ["egg", "clean water", "salt"], "tip": "???????????????????"},
    {"id": "cucumber_salad", "name": "????", "ingredients": ["cucumber", "salt"], "tip": "?????????????????"},
    {"id": "stir_fried_greens", "name": "???", "ingredients": ["green vegetable", "cooking oil", "salt"], "tip": "???????????????????"},
    {"id": "tofu_soup", "name": "???", "ingredients": ["tofu", "clean water", "salt"], "tip": "????????????????????"},
    {"id": "steamed_egg", "name": "???", "ingredients": ["egg", "clean water", "salt"], "tip": "????????????????"},
    {"id": "fried_rice", "name": "??", "ingredients": ["rice", "egg", "cooking oil", "salt"], "tip": "?????????????????????"},
    {"id": "fried_egg", "name": "???", "ingredients": ["egg", "cooking oil", "salt"], "tip": "??????????????????"},
    {"id": "seaweed_egg_soup", "name": "?????", "ingredients": ["seaweed", "egg", "clean water", "salt"], "tip": "????????????????????????"},
    {"id": "potato_chicken", "name": "????", "ingredients": ["potato", "chicken", "clean water", "salt"], "tip": "???????????????????"},
    {"id": "carrot_pork", "name": "?????", "ingredients": ["carrot", "pork", "cooking oil", "salt"], "tip": "??????????????????????"},
    {"id": "mixed_noodles", "name": "??", "ingredients": ["noodles", "clean water", "salt"], "tip": "?????????????????"},
    {"id": "porridge", "name": "?", "ingredients": ["rice", "clean water"], "tip": "???????????????"},
    {"id": "boiled_corn", "name": "???", "ingredients": ["corn", "clean water"], "tip": "??????????????????"},
    {"id": "sandwich", "name": "???", "ingredients": ["bread", "egg", "green vegetable", "salt"], "tip": "??????????????????"},
    {"id": "tomato_noodles", "name": "???", "ingredients": ["tomato", "noodles", "clean water", "salt"], "tip": "??????????????????"},
    {"id": "tofu_stir_fry", "name": "????", "ingredients": ["tofu", "cooking oil", "salt"], "tip": "??????????????????"},
]
COOKING_RECIPES = {
    "tomato_egg": [
        {"id": "collect", "name": "拿齐番茄、鸡蛋、食用油和盐", "commands": set(), "tip": "先在房间中找到并拿起番茄、鸡蛋、食用油和盐。"},
        {"id": "wash_tomato", "name": "洗番茄", "commands": {"洗番茄", "清洗番茄", "洗西红柿", "清洗西红柿"}, "tip": "番茄下锅前要先洗干净。"},
        {"id": "cut_tomato", "name": "切番茄", "commands": {"切番茄", "切西红柿"}, "tip": "洗好番茄后再切块，方便翻炒出汁。"},
        {"id": "beat_egg", "name": "打鸡蛋", "commands": {"打鸡蛋", "打蛋", "搅打鸡蛋"}, "tip": "番茄切好后，把鸡蛋打散备用。"},
        {"id": "heat_oil", "name": "热锅倒油", "commands": {"热锅", "倒油", "热锅倒油", "倒食用油"}, "tip": "先热锅并倒入食用油，再炒鸡蛋。"},
        {"id": "fry_egg", "name": "先炒鸡蛋", "commands": {"炒鸡蛋", "先炒鸡蛋"}, "tip": "油热后先把鸡蛋炒成块。"},
        {"id": "add_tomato", "name": "加入番茄", "commands": {"加入番茄", "加入西红柿", "放入番茄", "放入西红柿"}, "tip": "鸡蛋炒好后再加入番茄翻炒。"},
        {"id": "add_salt", "name": "加盐调味", "commands": {"加盐", "加盐调味", "放盐"}, "tip": "番茄炒出汁后加盐调味。"},
        {"id": "serve", "name": "出锅番茄炒蛋", "commands": {"出锅", "出锅番茄炒蛋", "完成番茄炒蛋", "做番茄炒蛋", "制作番茄炒蛋", "提交番茄炒蛋"}, "tip": "调味完成后就可以出锅番茄炒蛋。"},
    ],
    "rice": [
        {"id": "collect", "name": "拿齐大米和清水", "commands": set(), "tip": "先找到并拿起大米和清水。"},
        {"id": "rinse_rice", "name": "淘米", "commands": {"淘米", "洗米", "清洗大米"}, "tip": "煮饭前先把大米淘洗干净。"},
        {"id": "add_water", "name": "加水", "commands": {"加水", "加清水", "倒水", "加入清水", "拿水"}, "tip": "淘米后加入适量清水。"},
        {"id": "put_cooker", "name": "放入电饭煲", "commands": {"放入电饭煲", "放进电饭煲", "把米放入电饭煲", "放入锅中"}, "tip": "米和水准备好后放入电饭煲。"},
        {"id": "start_cooking", "name": "开始煮饭", "commands": {"开始煮饭", "煮饭", "启动电饭煲", "按下煮饭键"}, "tip": "盖好电饭煲并启动煮饭。"},
        {"id": "serve", "name": "盛出米饭", "commands": {"盛出米饭", "出锅米饭", "完成米饭", "做米饭", "制作米饭", "提交米饭"}, "tip": "米饭煮好后盛出。"},
    ],
    "vegetable_soup": [
        {"id": "collect", "name": "拿齐青菜、清水和盐", "commands": set(), "tip": "先找到并拿起青菜、清水和盐。"},
        {"id": "wash_vegetable", "name": "洗青菜", "commands": {"洗青菜", "清洗青菜"}, "tip": "青菜入锅前要洗干净。"},
        {"id": "cut_vegetable", "name": "切青菜", "commands": {"切青菜"}, "tip": "洗好青菜后切成适口大小。"},
        {"id": "boil_water", "name": "烧水", "commands": {"烧水", "煮水", "把水烧开", "烧开清水"}, "tip": "先把水烧开再放青菜。"},
        {"id": "add_vegetable", "name": "加入青菜", "commands": {"加入青菜", "放入青菜", "下青菜"}, "tip": "水开后加入青菜。"},
        {"id": "add_salt", "name": "加盐调味", "commands": {"加盐", "加盐调味", "放盐"}, "tip": "青菜煮熟后加盐调味。"},
        {"id": "serve", "name": "盛出青菜汤", "commands": {"盛出青菜汤", "出锅青菜汤", "完成青菜汤", "做青菜汤", "制作青菜汤", "提交青菜汤"}, "tip": "调味后盛出青菜汤。"},
    ],
}

FIRE_HAZARDS = [
    ("overloaded socket", "??????", "??????", "????????????????????"),
    ("open gas valve", "??????", "??????", "?????????????????"),
    ("blocked exit boxes", "????????", "??????", "???????????"),
    ("burning candle", "??????", "????", "?????????"),
    ("covered heater", "???????", "????", "????????????????"),
    ("old power cord", "?????", "?????", "??????????"),
    ("greasy stove", "????", "??????", "??????????"),
    ("smoking charger", "?????", "?????", "?????????????"),
    ("charger under pillow", "????????", "?????", "????????????"),
    ("paper near stove", "????????", "????", "????????????"),
    ("unattended oil pan", "??????", "????", "????????????"),
    ("indoor e-bike battery", "?????????", "??????", "?????????????"),
    ("balcony boxes near battery", "????????", "??????", "????????????"),
    ("missing smoke alarm", "???????", "???????", "?????????????"),
    ("wet socket", "????", "???????", "???????????"),
    ("curtain candle", "??????", "????", "????????????"),
    ("plugged hair dryer", "?????", "?????", "???????????"),
    ("electric blanket on", "?????", "?????", "????????????"),
    ("metal in microwave", "?????????", "??????", "????????????"),
    ("child with lighter", "??????", "?????", "????????????????"),
    ("expired extinguisher", "?????", "?????", "????????????"),
    ("corridor clutter", "??????", "??????", "?????????"),
    ("broken exit light", "???????", "???????", "???????????"),
]
GARBAGE_ITEMS = [
    ("apple core", "???", "????", "???????????????????"),
    ("old newspaper", "???", "????", "????????????"),
    ("used battery", "???", "????", "???????????????????"),
    ("dusty tissue", "???", "????", "???????????????"),
    ("plastic bottle", "???", "????", "???????????"),
    ("expired medicine", "????", "????", "???????????"),
    ("banana peel", "???", "????", "?????????"),
    ("broken ceramic bowl", "????", "????", "????????????????"),
    ("glass bottle", "???", "????", "??????????"),
    ("paint bucket", "???", "????", "??????????"),
    ("tea leaves", "???", "????", "??????????"),
    ("takeout box", "????", "????", "???????????????"),
    ("metal can", "???", "????", "????????"),
    ("fluorescent tube", "????", "????", "???????????????"),
    ("leftover rice", "???", "????", "???????????"),
    ("vegetable leaves", "??", "????", "?????????"),
    ("egg shell", "??", "????", "?????????"),
    ("delivery box", "????", "????", "?????????"),
    ("packing tape", "??", "????", "???????????"),
    ("milk tea cup", "???", "????", "????????????????"),
    ("plastic straw", "??", "????", "??????????????"),
    ("fish bone", "??", "????", "?????????"),
    ("pesticide can", "????", "????", "????????????"),
    ("shampoo bottle", "?????", "????", "???????????"),
    ("floor dust", "??", "????", "?????????"),
]

FIRE_SPECIAL_STEPS = {
    "overloaded_socket": ["?????", "??????", "??????", "????", "??????"],
    "open_gas_valve": ["????", "??????", "??????", "???????", "????"],
    "blocked_exit_boxes": ["????", "????", "?????", "??????"],
}
GARBAGE_PREPROCESS = {
    "plastic_bottle": "???????",
    "glass_bottle": "?????",
    "metal_can": "???????",
    "delivery_box": "??????",
    "milk_tea_cup": "?????",
    "shampoo_bottle": "???????",
    "broken_ceramic_bowl": "??????",
    "fluorescent_tube": "??????",
    "pesticide_can": "????????",
    "paint_bucket": "???????",
}
SCENE_STEP_ACTIONS = {"cook_step", "fix_step", "sort_step"}

CATEGORY_TO_BIN = {
    "厨余垃圾": "food waste bin",
    "可回收物": "recyclable bin",
    "有害垃圾": "hazardous waste bin",
    "其他垃圾": "other waste bin",
}

def repair_localized_targets():
    global COOKING_DISHES, FIRE_HAZARDS, GARBAGE_ITEMS, COOKING_RECIPES, FIRE_SPECIAL_STEPS, GARBAGE_PREPROCESS
    COOKING_DISHES = [
        {"id": "tomato_egg", "name": "\u756a\u8304\u7092\u86cb", "ingredients": ["tomato", "egg", "cooking oil", "salt"], "tip": "\u6309\u987a\u5e8f\u6d17\u5207\u756a\u8304\u3001\u6253\u86cb\u3001\u70ed\u9505\u5012\u6cb9\u3001\u7092\u86cb\u3001\u52a0\u756a\u8304\u548c\u76d0\u3002"},
        {"id": "rice", "name": "\u7c73\u996d", "ingredients": ["rice", "clean water"], "tip": "\u6dd8\u7c73\u3001\u52a0\u6c34\u3001\u653e\u5165\u7535\u996d\u7172\u5e76\u716e\u719f\u3002"},
        {"id": "vegetable_soup", "name": "\u9752\u83dc\u6c64", "ingredients": ["green vegetable", "clean water", "salt"], "tip": "\u6d17\u5207\u9752\u83dc\u3001\u70e7\u6c34\u3001\u52a0\u9752\u83dc\u548c\u76d0\u3002"},
    ]
    cooking_variants = [
        ("potato_shreds", "\u571f\u8c46\u4e1d", ["potato", "cooking oil", "salt"]),
        ("carrot_egg", "\u80e1\u841d\u535c\u7092\u86cb", ["carrot", "egg", "cooking oil", "salt"]),
        ("noodles", "\u716e\u9762\u6761", ["noodles", "clean water", "salt"]),
        ("egg_soup", "\u9e21\u86cb\u6c64", ["egg", "clean water", "salt"]),
        ("cucumber_salad", "\u51c9\u62cc\u9ec4\u74dc", ["cucumber", "salt"]),
        ("stir_fried_greens", "\u7092\u9752\u83dc", ["green vegetable", "cooking oil", "salt"]),
        ("tofu_soup", "\u8c46\u8150\u6c64", ["tofu", "clean water", "salt"]),
        ("steamed_egg", "\u84b8\u9e21\u86cb", ["egg", "clean water", "salt"]),
        ("fried_rice", "\u7092\u996d", ["rice", "egg", "cooking oil", "salt"]),
        ("fried_egg", "\u714e\u9e21\u86cb", ["egg", "cooking oil", "salt"]),
        ("seaweed_egg_soup", "\u7d2b\u83dc\u86cb\u82b1\u6c64", ["seaweed", "egg", "clean water", "salt"]),
        ("potato_chicken", "\u571f\u8c46\u7096\u9e21", ["potato", "chicken", "clean water", "salt"]),
        ("carrot_pork", "\u80e1\u841d\u535c\u7092\u8089", ["carrot", "pork", "cooking oil", "salt"]),
        ("mixed_noodles", "\u62cc\u9762", ["noodles", "clean water", "salt"]),
        ("porridge", "\u7ca5", ["rice", "clean water"]),
        ("boiled_corn", "\u716e\u7389\u7c73", ["corn", "clean water"]),
        ("sandwich", "\u4e09\u660e\u6cbb", ["bread", "egg", "green vegetable", "salt"]),
        ("tomato_noodles", "\u756a\u8304\u9762", ["tomato", "noodles", "clean water", "salt"]),
        ("tofu_stir_fry", "\u5bb6\u5e38\u8c46\u8150", ["tofu", "cooking oil", "salt"]),
    ]
    COOKING_DISHES.extend({"id": item_id, "name": name, "ingredients": ingredients, "tip": f"{name}\u9700\u8981\u6309\u5907\u6599\u3001\u5904\u7406\u3001\u70f9\u5236\u3001\u5b8c\u6210\u7684\u987a\u5e8f\u64cd\u4f5c\u3002"} for item_id, name, ingredients in cooking_variants)
    FIRE_HAZARDS = [
        ("overloaded socket", "\u8d85\u8d1f\u8377\u63d2\u7ebf\u677f", "\u62d4\u6389\u591a\u4f59\u63d2\u5934", "\u4e0d\u8981\u5728\u4e00\u4e2a\u63d2\u7ebf\u677f\u4e0a\u540c\u65f6\u63a5\u592a\u591a\u5927\u529f\u7387\u7535\u5668\u3002"),
        ("open gas valve", "\u71c3\u6c14\u9600\u95e8\u672a\u5173", "\u5173\u95ed\u71c3\u6c14\u9600\u95e8", "\u79bb\u5f00\u53a8\u623f\u6216\u7761\u524d\u8981\u786e\u8ba4\u71c3\u6c14\u9600\u95e8\u5173\u95ed\u3002"),
        ("blocked exit boxes", "\u9003\u751f\u901a\u9053\u5806\u6ee1\u7eb8\u7bb1", "\u6e05\u7406\u9003\u751f\u901a\u9053", "\u9003\u751f\u901a\u9053\u5fc5\u987b\u4fdd\u6301\u7545\u901a\u3002"),
    ]
    fire_names = ["\u672a\u7184\u706d\u7684\u8721\u70db", "\u53d6\u6696\u5668\u8986\u76d6\u8863\u7269", "\u8001\u5316\u7535\u6e90\u7ebf", "\u7076\u53f0\u6cb9\u6c61", "\u5192\u70df\u5145\u7535\u5668", "\u5145\u7535\u5668\u538b\u5728\u6795\u5934\u4e0b", "\u53a8\u623f\u7eb8\u5dfe\u9760\u8fd1\u7076\u53f0", "\u6cb9\u9505\u65e0\u4eba\u770b\u7ba1", "\u7535\u52a8\u8f66\u7535\u6c60\u5ba4\u5185\u5145\u7535", "\u9633\u53f0\u7eb8\u7bb1\u9760\u8fd1\u7535\u6c60", "\u70df\u96fe\u62a5\u8b66\u5668\u7f3a\u5931", "\u63d2\u5ea7\u8fdb\u6c34", "\u8721\u70db\u9760\u8fd1\u7a97\u5e18", "\u5439\u98ce\u673a\u672a\u62d4", "\u7535\u70ed\u6bef\u672a\u5173", "\u5fae\u6ce2\u7089\u5185\u6709\u91d1\u5c5e\u9910\u5177", "\u513f\u7ae5\u73a9\u6253\u706b\u673a", "\u706d\u706b\u5668\u8fc7\u671f", "\u697c\u9053\u6742\u7269\u5835\u585e", "\u5b89\u5168\u51fa\u53e3\u706f\u635f\u574f"]
    FIRE_HAZARDS.extend((f"hazard variant {index}", name, f"\u5904\u7406{name}", f"{name}\u9700\u8981\u6309\u5b89\u5168\u6b65\u9aa4\u6392\u9664\u3002") for index, name in enumerate(fire_names, start=1))
    GARBAGE_ITEMS = [
        ("apple core", "\u82f9\u679c\u6838", "\u53a8\u4f59\u5783\u573e", "\u82f9\u679c\u6838\u5c5e\u4e8e\u53a8\u4f59\u5783\u573e\u3002"),
        ("old newspaper", "\u65e7\u62a5\u7eb8", "\u53ef\u56de\u6536\u7269", "\u5e72\u51c0\u7eb8\u5f20\u53ef\u56de\u6536\u3002"),
        ("used battery", "\u5e9f\u7535\u6c60", "\u6709\u5bb3\u5783\u573e", "\u5e9f\u7535\u6c60\u5c5e\u4e8e\u6709\u5bb3\u5783\u573e\u3002"),
        ("dusty tissue", "\u810f\u7eb8\u5dfe", "\u5176\u4ed6\u5783\u573e", "\u810f\u7eb8\u5dfe\u5c5e\u4e8e\u5176\u4ed6\u5783\u573e\u3002"),
    ]
    garbage_more = [("plastic bottle", "\u5851\u6599\u74f6", "\u53ef\u56de\u6536\u7269"), ("tea leaves", "\u8336\u53f6\u6e23", "\u53a8\u4f59\u5783\u573e"), ("glass bottle", "\u73bb\u7483\u74f6", "\u53ef\u56de\u6536\u7269"), ("metal can", "\u6613\u62c9\u7f50", "\u53ef\u56de\u6536\u7269"), ("expired medicine", "\u8fc7\u671f\u836f\u54c1", "\u6709\u5bb3\u5783\u573e"), ("fluorescent tube", "\u8367\u5149\u706f\u7ba1", "\u6709\u5bb3\u5783\u573e"), ("vegetable leaves", "\u83dc\u53f6", "\u53a8\u4f59\u5783\u573e"), ("egg shell", "\u86cb\u58f3", "\u53a8\u4f59\u5783\u573e"), ("delivery box", "\u5feb\u9012\u7eb8\u7bb1", "\u53ef\u56de\u6536\u7269"), ("packing tape", "\u80f6\u5e26", "\u5176\u4ed6\u5783\u573e"), ("milk tea cup", "\u5976\u8336\u676f", "\u5176\u4ed6\u5783\u573e"), ("plastic straw", "\u5438\u7ba1", "\u5176\u4ed6\u5783\u573e"), ("leftover rice", "\u5269\u7c73\u996d", "\u53a8\u4f59\u5783\u573e"), ("fish bone", "\u9c7c\u9aa8", "\u53a8\u4f59\u5783\u573e"), ("broken ceramic bowl", "\u788e\u9676\u74f7\u7897", "\u5176\u4ed6\u5783\u573e"), ("pesticide can", "\u6740\u866b\u5242\u7f50", "\u6709\u5bb3\u5783\u573e"), ("shampoo bottle", "\u6d17\u53d1\u6c34\u7a7a\u74f6", "\u53ef\u56de\u6536\u7269"), ("floor dust", "\u5c18\u571f", "\u5176\u4ed6\u5783\u573e"), ("paint bucket", "\u6cb9\u6f06\u6876", "\u6709\u5bb3\u5783\u573e"), ("banana peel", "\u9999\u8549\u76ae", "\u53a8\u4f59\u5783\u573e")]
    GARBAGE_ITEMS.extend((en, cn, cat, f"{cn}\u5e94\u6295\u653e\u5230{cat}\u3002") for en, cn, cat in garbage_more)
    FIRE_SPECIAL_STEPS = {
        "overloaded_socket": ["\u89c2\u5bdf\u63d2\u7ebf\u677f", "\u5173\u95ed\u76f8\u5173\u7535\u5668", "\u62d4\u6389\u591a\u4f59\u63d2\u5934", "\u6574\u7406\u7ebf\u8def", "\u786e\u8ba4\u9690\u60a3\u89e3\u9664"],
        "open_gas_valve": ["\u89c2\u5bdf\u7076\u53f0", "\u5173\u95ed\u71c3\u6c14\u9600\u95e8", "\u6253\u5f00\u7a97\u6237\u901a\u98ce", "\u4e0d\u89e6\u78b0\u660e\u706b\u7535\u6e90", "\u786e\u8ba4\u5b89\u5168"],
        "blocked_exit_boxes": ["\u89c2\u5bdf\u901a\u9053", "\u79fb\u5f00\u7eb8\u7bb1", "\u6e05\u7406\u53ef\u71c3\u7269", "\u786e\u8ba4\u901a\u9053\u7545\u901a"],
    }
    GARBAGE_PREPROCESS = {"plastic_bottle": "\u6e05\u7a7a\u538b\u6241\u5851\u6599\u74f6", "delivery_box": "\u538b\u6241\u5feb\u9012\u7eb8\u7bb1", "milk_tea_cup": "\u6e05\u7a7a\u5976\u8336\u676f", "shampoo_bottle": "\u6e05\u7a7a\u6d17\u53d1\u6c34\u7a7a\u74f6", "broken_ceramic_bowl": "\u5305\u597d\u788e\u9676\u74f7\u7897", "fluorescent_tube": "\u5305\u597d\u8367\u5149\u706f\u7ba1", "pesticide_can": "\u786e\u8ba4\u6740\u866b\u5242\u7f50\u5bc6\u5c01", "paint_bucket": "\u786e\u8ba4\u6cb9\u6f06\u6876\u5bc6\u5c01"}

repair_localized_targets()

BIN_CN_TO_EN = {k: v for k, v in CATEGORY_TO_BIN.items()}
CN_TO_EN = {
    "番茄": "tomato", "西红柿": "tomato", "鸡蛋": "egg", "食用油": "cooking oil", "油": "cooking oil",
    "大米": "rice", "清水": "clean water", "水": "clean water", "盐": "salt", "青菜": "green vegetable",
    "土豆": "potato", "胡萝卜": "carrot", "面条": "noodles", "黄瓜": "cucumber", "豆腐": "tofu",
    "紫菜": "seaweed", "鸡肉": "chicken", "猪肉": "pork", "玉米": "corn", "面包": "bread",
    "白菜": "cabbage", "香菇": "mushroom", "韭菜": "chive", "红薯": "sweet potato",
}

INGREDIENT_CN = {
    "tomato": "番茄",
    "egg": "鸡蛋",
    "cooking oil": "油",
    "salt": "盐",
    "rice": "大米",
    "clean water": "水",
    "green vegetable": "青菜",
    "potato": "土豆",
    "carrot": "胡萝卜",
    "noodles": "面条",
    "cucumber": "黄瓜",
    "tofu": "豆腐",
    "seaweed": "紫菜",
    "chicken": "鸡肉",
    "pork": "猪肉",
    "corn": "玉米",
    "bread": "面包",
    "cabbage": "白菜",
    "mushroom": "香菇",
    "chive": "韭菜",
    "sweet potato": "红薯",
}
for dish in COOKING_DISHES:
    CN_TO_EN[dish["name"]] = dish["id"].replace("_", " ")
for english, chinese, _action, _tip in FIRE_HAZARDS:
    CN_TO_EN[chinese] = english
for english, chinese, category, _tip in GARBAGE_ITEMS:
    CN_TO_EN[chinese] = english
    CN_TO_EN[category] = CATEGORY_TO_BIN[category]
CN_TO_EN.update(BIN_CN_TO_EN)
EN_TO_CN = {english: chinese for chinese, english in CN_TO_EN.items() if chinese not in CATEGORY_TO_BIN}

GAME_SCENARIOS = {
    "cooking": {"id": "cooking", "name": "烹制菜品", "description": "收集食材并完成目标菜品。", "difficulties": {"easy": {"rooms": 2, "targets": 1}, "medium": {"rooms": 3, "targets": 2}, "hard": {"rooms": 4, "targets": 3}}},
    "fire_safety": {"id": "fire_safety", "name": "防患火灾隐患", "description": "巡视房间并处理安全隐患。", "difficulties": {"easy": {"rooms": 2, "targets": 3}, "medium": {"rooms": 3, "targets": 5}, "hard": {"rooms": 4, "targets": 8}}},
    "garbage_sorting": {"id": "garbage_sorting", "name": "垃圾分类", "description": "拾取垃圾并投放到正确类别。", "difficulties": {"easy": {"rooms": 2, "targets": 5}, "medium": {"rooms": 3, "targets": 10}, "hard": {"rooms": 4, "targets": 15}}},
}

game_sessions: dict[str, dict] = {}


def find_tw_make():
    return shutil.which("tw-make") or str(next(Path(sys.prefix, "Scripts").glob("tw-make*"), "")) or None


def normalize(text):
    return re.sub(r"\s+", "_", str(text or "").strip().lower())


def split_command(command):
    normalized = normalize(command)
    return normalized, [part for part in normalized.split("_") if part]


def public_scenarios():
    scenarios = deepcopy(GAME_SCENARIOS)
    labels = {"easy": "低难度", "medium": "中难度", "hard": "高难度"}
    for scenario in scenarios.values():
        for key, config in scenario["difficulties"].items():
            config["id"] = key
            config["name"] = labels[key]
    return scenarios


def ensure_textworld_available():
    if textworld is None:
        raise RuntimeError(f"TextWorld 导入失败：{TEXTWORLD_IMPORT_ERROR}")


def build_connections(rooms, rng=None):
    if rng is not None:
        return build_random_connections(rooms, rng)
    exits = {room["id"]: {} for room in rooms}
    edges = []
    for direction, from_index, to_index in CONNECTION_PATTERNS[len(rooms)]:
        from_room = rooms[from_index]["id"]
        to_room = rooms[to_index]["id"]
        exits[from_room][direction] = to_room
        exits[to_room][OPPOSITE[direction]] = from_room
        edges.append({"from": from_room, "to": to_room, "direction": direction})
    return {"exits": exits, "edges": edges}


def build_random_connections(rooms, rng):
    exits = {room["id"]: {} for room in rooms}
    edges = []
    room_positions = {(room["x"], room["y"]): room for room in rooms}
    candidate_edges = []
    for room in rooms:
        east = room_positions.get((room["x"] + 1, room["y"]))
        south = room_positions.get((room["x"], room["y"] + 1))
        if east:
            candidate_edges.append(("east", room["id"], east["id"]))
        if south:
            candidate_edges.append(("south", room["id"], south["id"]))
    rng.shuffle(candidate_edges)

    parent = {room["id"]: room["id"] for room in rooms}

    def find(room_id):
        while parent[room_id] != room_id:
            parent[room_id] = parent[parent[room_id]]
            room_id = parent[room_id]
        return room_id

    def union(left, right):
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return False
        parent[right_root] = left_root
        return True

    chosen = []
    for edge in candidate_edges:
        if union(edge[1], edge[2]):
            chosen.append(edge)
        if len(chosen) == len(rooms) - 1:
            break
    for edge in candidate_edges:
        if edge not in chosen and rng.random() < 0.45:
            chosen.append(edge)
    if not chosen and len(rooms) == 1:
        return {"exits": exits, "edges": []}
    for direction, from_room, to_room in chosen:
        exits[from_room][direction] = to_room
        exits[to_room][OPPOSITE[direction]] = from_room
        edges.append({"from": from_room, "to": to_room, "direction": direction})
    return {"exits": exits, "edges": edges}


def scenario_targets(scenario_id, difficulty, rng=None):
    count = GAME_SCENARIOS[scenario_id]["difficulties"][difficulty]["targets"]
    if scenario_id == "cooking":
        pool = list(COOKING_DISHES)
        selected = (rng.sample(pool, count) if rng else pool[:count])
        return [{
            "id": dish["id"],
            "name": dish["name"],
            "type": "dish",
            "requiredItems": dish["ingredients"],
            "requiredTools": ["pan", "spatula"] if dish["id"] == "tomato_egg" else [],
            "ingredients": dish["ingredients"],
            "difficultyTags": [difficulty],
            "knowledgePoint": dish["tip"],
            "successFeedback": f"{dish['name']}完成！记住按步骤备料、处理、烹制和收尾。",
            "wrongOrderHint": "顺序不对，请先完成当前提示的步骤。",
            "tip": dish["tip"],
        } for dish in selected]
    if scenario_id == "fire_safety":
        pool = list(FIRE_HAZARDS)
        selected = (rng.sample(pool, count) if rng else pool[:count])
        return [{
            "id": normalize(en),
            "name": cn,
            "english": en,
            "type": "hazard",
            "solutionAction": action,
            "action": action,
            "difficultyTags": [difficulty],
            "knowledgePoint": tip,
            "successFeedback": f"{cn}已排除，火灾风险降低。",
            "wrongOrderHint": "处理隐患要先观察，再采取对应措施，最后确认安全。",
            "tip": tip,
        } for en, cn, action, tip in selected]
    pool = list(GARBAGE_ITEMS)
    selected = (rng.sample(pool, count) if rng else pool[:count])
    return [{
        "id": normalize(en),
        "name": cn,
        "english": en,
        "type": "garbage",
        "correctBin": category,
        "category": category,
        "bin": CATEGORY_TO_BIN[category],
        "requiresPreprocess": normalize(en) in GARBAGE_PREPROCESS,
        "difficultyTags": [difficulty],
        "knowledgePoint": tip,
        "successFeedback": f"{cn}分类正确，应投放到{category}。",
        "wrongOrderHint": "垃圾分类前先判断类别，复合包装要先预处理。",
        "tip": tip,
    } for en, cn, category, tip in selected]


def build_world_metadata(scenario_id, difficulty, seed=None):
    rng = random.Random(seed) if seed is not None else None
    room_count = GAME_SCENARIOS[scenario_id]["difficulties"][difficulty]["rooms"]
    room_pool = deepcopy(ROOM_LIBRARY[scenario_id])
    if rng:
        rooms = rng.sample(room_pool, room_count)
        for index, room in enumerate(rooms):
            room["x"] = index % 2
            room["y"] = index // 2
    else:
        rooms = room_pool[:room_count]
    connections = build_connections(rooms, rng)
    targets = scenario_targets(scenario_id, difficulty, rng)
    for room in rooms:
        room["items"] = []
        room["exits"] = connections["exits"].get(room["id"], {})
    target_rooms = [rng.choice(rooms) for _ in targets] if rng else [rooms[index % len(rooms)] for index, _target in enumerate(targets)]
    for target, room in zip(targets, target_rooms):
        room["items"].append({"id": target["id"], "name": target["name"], "type": target["type"]})
    start_room = rng.choice(rooms)["id"] if rng else rooms[0]["id"]
    return {"rooms": rooms, "connections": connections["edges"], "targets": targets, "startRoom": start_room, "seed": seed}


def add_room_items(maker, room_entities, world, targets, scenario_id):
    entity_by_target = {}
    room_by_item = {
        item["id"]: room["id"]
        for room in world["rooms"]
        for item in room.get("items", [])
    }
    for target in targets:
        room = room_entities[room_by_item.get(target["id"], world["startRoom"])]
        if scenario_id == "cooking":
            for ingredient in target["ingredients"]:
                if ingredient in entity_by_target:
                    continue
                item = maker.new(type="o", name=ingredient)
                room.add(item)
                entity_by_target[ingredient] = item
        else:
            name = target.get("english", target["name"])
            item = maker.new(type="o", name=name)
            room.add(item)
            entity_by_target[target["id"]] = item
    return entity_by_target


def create_textworld_game_file(scenario_id, difficulty, world, game_id):
    ensure_textworld_available()
    maker = GameMaker()
    room_entities = {room["id"]: maker.new_room(room["name"]) for room in world["rooms"]}
    maker.set_player(room_entities[world["startRoom"]])
    for edge in world["connections"]:
        maker.connect(getattr(room_entities[edge["from"]], edge["direction"]), getattr(room_entities[edge["to"]], OPPOSITE[edge["direction"]]))

    targets = world["targets"]
    entity_by_target = add_room_items(maker, room_entities, world, targets, scenario_id)
    quests = []
    walkthrough = []

    if scenario_id == "cooking":
        for target in targets:
            conditions = {maker.new_fact("in", entity_by_target[ingredient], maker.inventory) for ingredient in target["ingredients"]}
            quests.append(Quest(win_events=[Event(conditions=conditions)], reward=1))
            walkthrough.extend([f"take {ingredient}" for ingredient in target["ingredients"]])
    elif scenario_id == "fire_safety":
        for target in targets:
            item = entity_by_target[target["id"]]
            quests.append(Quest(win_events=[Event(conditions={maker.new_fact("in", item, maker.inventory)})], reward=1))
            walkthrough.append(f"take {target['english']}")
    else:
        bins = {}
        bin_entities_by_room = {}
        for category, bin_name in CATEGORY_TO_BIN.items():
            for room_id, room_entity in room_entities.items():
                bin_entity = maker.new(type="c", name=bin_name)
                bin_entity.add_property("open")
                room_entity.add(bin_entity)
                bin_entities_by_room[(room_id, category)] = bin_entity
        for target in targets:
            item = entity_by_target[target["id"]]
            target_room_id = next(room["id"] for room in world["rooms"] if any(item_meta["id"] == target["id"] for item_meta in room.get("items", [])))
            bin_entity = bin_entities_by_room[(target_room_id, target["category"])]
            quests.append(Quest(win_events=[Event(conditions={maker.new_fact("in", item, bin_entity)})], reward=1))
            walkthrough.extend([f"take {target['english']}", f"insert {target['english']} into {target['bin']}"])

    maker.quests = quests
    game = maker.build()
    game.metadata.update({"scenario": scenario_id, "difficulty": difficulty, "world": world, "walkthrough": walkthrough})
    game.objective = build_objective(scenario_id, targets)
    game_file = GENERATED_GAMES_DIR / f"{game_id}.json"
    game.save(str(game_file))
    return game_file


def build_objective(scenario_id, targets):
    if scenario_id == "cooking":
        return "收集食材并完成：" + "、".join(target["name"] for target in targets)
    if scenario_id == "fire_safety":
        return "处理以下火灾隐患：" + "、".join(target["name"] for target in targets)
    return "把垃圾投放到正确类别：" + "、".join(f"{target['name']}→{target['category']}" for target in targets)


def get_or_create_game_file(scenario_id, difficulty, world, game_id):
    return create_textworld_game_file(scenario_id, difficulty, world, game_id)


def make_env(game_file):
    ensure_textworld_available()
    infos = EnvInfos(
        admissible_commands=True,
        facts=True,
        inventory=True,
        location=True,
        score=True,
        moves=True,
        objective=True,
        max_score=True,
        policy_commands=True,
        intermediate_reward=True,
        last_action=True,
    )
    env = textworld.start(str(game_file), request_infos=infos)
    state = env.reset()
    return env, state


def create_session(scenario_id, difficulty, game_id=None, seed=None):
    game_id = game_id or str(uuid.uuid4())
    seed = seed if seed is not None else random.SystemRandom().randrange(1, 2**31)
    world = build_world_metadata(scenario_id, difficulty, seed)
    game_file = get_or_create_game_file(scenario_id, difficulty, world, game_id)
    env, tw_state = make_env(game_file)
    return {
        "scenario": scenario_id,
        "difficulty": difficulty,
        "engine": "textworld-json",
        "game_file": str(game_file),
        "seed": seed,
        "world": world,
        "env": env,
        "tw_state": tw_state,
        "currentRoom": world["startRoom"],
        "visitedRooms": {world["startRoom"]},
        "completedTargetIds": set(),
        "mistakes": 0,
        "last_score": 0,
        "done": False,
    }


def get_room(session, room_id):
    return next(room for room in session["world"]["rooms"] if room["id"] == room_id)


def textworld_inventory_names(tw_state):
    inventory = getattr(tw_state, "inventory", None)
    if isinstance(inventory, str):
        return [] if inventory.lower() in {"nothing", "empty"} else [inventory]
    facts = getattr(tw_state, "facts", []) or []
    names = []
    for fact in facts:
        text = str(fact)
        match = re.match(r"in\((.*?)(?:: [a-z])?, I\)", text)
        if match:
            names.append(match.group(1))
    return names


def completed_target_ids(session):
    facts = {str(fact) for fact in (getattr(session["tw_state"], "facts", []) or [])}
    def fact_contains(item, holder):
        return any(re.fullmatch(rf"in\({re.escape(item)}(?:: [a-z])?, {re.escape(holder)}(?:: [a-z])?\)", fact) for fact in facts)
    completed = set()
    for target in session["world"]["targets"]:
        if session["scenario"] == "cooking":
            if cooking_target_completed(session, target):
                completed.add(target["id"])
        elif session["scenario"] in {"fire_safety", "garbage_sorting"}:
            if target_completed_by_steps(session, target):
                completed.add(target["id"])
    session["completedTargetIds"] = completed
    return completed


def cooking_recipe(target):
    return deepcopy(generic_cooking_recipe(target))


def z(text):
    return text.encode("ascii").decode("unicode_escape")


def cooking_step(step_id, name, tip, commands=None):
    base = set(command_variants(name))
    if commands:
        for command in commands:
            base |= command_variants(command)
    return {"id": step_id, "name": name, "commands": base, "tip": tip}


def collect_cooking_step(target, ingredient_names):
    separator = z(r"\u3001")
    collect_commands = {z(r"\u62ff\u9f50") + separator.join(ingredient_names)}
    for name in ingredient_names:
        collect_commands |= {z(r"\u62ff") + name, z(r"\u62ff\u8d77") + name, z(r"\u62fe\u53d6") + name}
    return cooking_step("collect", z(r"\u62ff\u9f50") + separator.join(ingredient_names), z(r"\u5148\u627e\u5230\u5e76\u62ff\u8d77\u6240\u6709\u9700\u8981\u7684\u98df\u6750\u3002"), collect_commands)


def ingredient_label(target, fallback=None):
    separator = z(r"\u3001")
    names = [INGREDIENT_CN.get(item, EN_TO_CN.get(item, item)) for item in target["ingredients"] if item not in {"cooking oil", "salt", "clean water"}]
    return fallback or (separator.join(names) if names else target["name"])


def generic_cooking_recipe(target):
    ingredient_names = [INGREDIENT_CN.get(item, EN_TO_CN.get(item, item)) for item in target["ingredients"]]
    recipe = [collect_cooking_step(target, ingredient_names)]
    dish_id = target["id"]
    dish_name = target["name"]
    main = ingredient_label(target)
    egg = z(r"\u9e21\u86cb")
    water = z(r"\u6e05\u6c34")
    noodles = z(r"\u9762\u6761")
    tomato = z(r"\u756a\u8304")
    tofu = z(r"\u8c46\u8150")
    corn = z(r"\u7389\u7c73")
    potato = z(r"\u571f\u8c46")
    chicken = z(r"\u9e21\u8089")
    vegetable = z(r"\u9752\u83dc")
    cucumber = z(r"\u9ec4\u74dc")

    stir_fry = {"tomato_egg", "potato_shreds", "carrot_egg", "stir_fried_greens", "fried_rice", "carrot_pork", "tofu_stir_fry"}
    soups = {"vegetable_soup", "egg_soup", "tofu_soup", "seaweed_egg_soup", "tomato_noodles"}
    boiled = {"noodles", "porridge", "boiled_corn", "rice"}
    salads = {"cucumber_salad", "mixed_noodles", "sandwich"}

    if dish_id == "fried_egg":
        recipe += [
            cooking_step("beat_egg", z(r"\u6253\u6563\u9e21\u86cb"), z(r"\u5148\u628a\u9e21\u86cb\u6253\u5165\u7897\u4e2d\u5e76\u6405\u6563\u3002"), {z(r"\u6253\u9e21\u86cb"), z(r"\u6253\u86cb"), z(r"\u6405\u6253\u9e21\u86cb"), z(r"\u6253\u6563\u9e21\u86cb")}),
            cooking_step("heat_pan", z(r"\u70ed\u9505"), z(r"\u5148\u628a\u9505\u70e7\u70ed\uff0c\u907f\u514d\u9e21\u86cb\u7c98\u9505\u3002"), {z(r"\u70ed\u9505"), z(r"\u70e7\u70ed\u9505")}),
            cooking_step("add_oil", z(r"\u5012\u6cb9"), z(r"\u9505\u70ed\u540e\u5012\u5165\u5c11\u91cf\u98df\u7528\u6cb9\u3002"), {z(r"\u5012\u6cb9"), z(r"\u5012\u98df\u7528\u6cb9"), z(r"\u4e0b\u6cb9")}),
            cooking_step("pour_egg", z(r"\u4e0b\u9e21\u86cb"), z(r"\u6cb9\u70ed\u540e\u628a\u86cb\u6db2\u5012\u5165\u9505\u4e2d\u3002"), {z(r"\u4e0b\u9e21\u86cb"), z(r"\u5012\u5165\u9e21\u86cb"), z(r"\u5012\u5165\u86cb\u6db2"), z(r"\u4e0b\u86cb")}),
            cooking_step("fry_until_done", z(r"\u7ffb\u9762\u714e\u719f"), z(r"\u4e00\u9762\u5b9a\u578b\u540e\u7ffb\u9762\uff0c\u628a\u9e21\u86cb\u714e\u719f\u3002"), {z(r"\u7ffb\u9762"), z(r"\u7ffb\u9762\u714e\u719f"), z(r"\u714e\u719f"), z(r"\u714e\u719f\u9e21\u86cb")}),
            cooking_step("plate", z(r"\u76db\u51fa\u714e\u9e21\u86cb"), z(r"\u714e\u719f\u540e\u53ca\u65f6\u76db\u51fa\u88c5\u76d8\u3002"), {z(r"\u76db\u51fa"), z(r"\u88c5\u76d8"), z(r"\u76db\u51fa\u714e\u9e21\u86cb"), z(r"\u88c5\u76d8\u714e\u9e21\u86cb")}),
        ]
    elif dish_id == "steamed_egg":
        recipe += [
            cooking_step("beat_egg", z(r"\u6253\u6563\u9e21\u86cb"), z(r"\u5148\u628a\u9e21\u86cb\u6253\u6563\u3002"), {z(r"\u6253\u9e21\u86cb"), z(r"\u6253\u86cb"), z(r"\u6405\u6253\u9e21\u86cb"), z(r"\u6253\u6563\u9e21\u86cb")}),
            cooking_step("add_water", z(r"\u52a0\u5165\u6e05\u6c34"), z(r"\u5f80\u86cb\u6db2\u4e2d\u52a0\u5165\u9002\u91cf\u6e05\u6c34\u5e76\u6405\u5300\u3002"), {z(r"\u52a0\u6c34"), z(r"\u52a0\u5165\u6e05\u6c34"), z(r"\u5012\u6c34"), z(r"\u86cb\u6db2\u52a0\u6c34")}),
            cooking_step("put_steamer", z(r"\u653e\u5165\u84b8\u9505"), z(r"\u628a\u86cb\u6db2\u7897\u653e\u5165\u84b8\u9505\u6216\u84b8\u5c49\u3002"), {z(r"\u653e\u5165\u84b8\u9505"), z(r"\u653e\u8fdb\u84b8\u9505"), z(r"\u653e\u5165\u9505\u5177"), z(r"\u4e0a\u9505")}),
            cooking_step("start_steam", z(r"\u5f00\u59cb\u84b8\u86cb"), z(r"\u76d6\u597d\u9505\u76d6\u540e\u5f00\u59cb\u84b8\u3002"), {z(r"\u5f00\u59cb\u84b8"), z(r"\u5f00\u59cb\u84b8\u86cb"), z(r"\u84b8\u9e21\u86cb"), z(r"\u5f00\u706b\u84b8\u86cb")}),
            cooking_step("wait_done", z(r"\u7b49\u5f85\u84b8\u719f"), z(r"\u7b49\u5f85\u86cb\u7fb9\u5b8c\u5168\u51dd\u56fa\u719f\u900f\u3002"), {z(r"\u7b49\u5f85\u84b8\u719f"), z(r"\u84b8\u719f"), z(r"\u7b49\u84b8\u719f"), z(r"\u7b49\u5f85\u719f\u900f")}),
            cooking_step("serve", z(r"\u76db\u51fa\u84b8\u9e21\u86cb"), z(r"\u84b8\u719f\u540e\u5c0f\u5fc3\u76db\u51fa\u3002"), {z(r"\u76db\u51fa"), z(r"\u76db\u51fa\u84b8\u9e21\u86cb"), z(r"\u53d6\u51fa\u84b8\u9e21\u86cb"), z(r"\u88c5\u76d8")}),
        ]
    elif dish_id in soups:
        add_items = {"vegetable_soup": vegetable, "egg_soup": egg, "tofu_soup": tofu, "seaweed_egg_soup": z(r"\u7d2b\u83dc\u548c\u86cb\u6db2"), "tomato_noodles": z(r"\u756a\u8304\u548c\u9762\u6761")}.get(dish_id, main)
        if dish_id in {"egg_soup", "seaweed_egg_soup"}:
            recipe.append(cooking_step("beat_egg", z(r"\u6253\u6563\u9e21\u86cb"), z(r"\u5148\u628a\u9e21\u86cb\u6253\u6563\uff0c\u65b9\u4fbf\u5f62\u6210\u86cb\u82b1\u3002"), {z(r"\u6253\u9e21\u86cb"), z(r"\u6253\u86cb"), z(r"\u6405\u6253\u9e21\u86cb"), z(r"\u6253\u6563\u9e21\u86cb")}))
        if dish_id == "tomato_noodles":
            recipe.append(cooking_step("cut_tomato", z(r"\u5207\u756a\u8304"), z(r"\u5148\u628a\u756a\u8304\u5207\u5757\uff0c\u65b9\u4fbf\u716e\u51fa\u6c64\u6c41\u3002"), {z(r"\u5207\u756a\u8304"), z(r"\u5207\u897f\u7ea2\u67ff")}))
        recipe += [
            cooking_step("add_water", z(r"\u9505\u4e2d\u52a0\u6c34"), z(r"\u5148\u5f80\u9505\u4e2d\u52a0\u5165\u6e05\u6c34\u3002"), {z(r"\u52a0\u6c34"), z(r"\u9505\u4e2d\u52a0\u6c34"), z(r"\u52a0\u5165\u6e05\u6c34"), z(r"\u5012\u6c34")}),
            cooking_step("boil_water", z(r"\u70e7\u5f00\u6e05\u6c34"), z(r"\u628a\u9505\u91cc\u7684\u6c34\u70e7\u5f00\u3002"), {z(r"\u70e7\u6c34"), z(r"\u716e\u6c34"), z(r"\u70e7\u5f00"), z(r"\u70e7\u5f00\u6e05\u6c34")}),
            cooking_step("add_main", z(r"\u4e0b") + add_items, z(r"\u6c34\u5f00\u540e\u518d\u4e0b") + add_items + z(r"\u3002"), {z(r"\u4e0b") + add_items, z(r"\u52a0\u5165") + add_items, z(r"\u653e\u5165") + add_items}),
            cooking_step("season", z(r"\u52a0\u76d0\u8c03\u5473"), z(r"\u98df\u6750\u716e\u719f\u540e\u52a0\u5165\u76d0\u8c03\u5473\u3002"), {z(r"\u52a0\u76d0"), z(r"\u52a0\u76d0\u8c03\u5473"), z(r"\u653e\u76d0"), z(r"\u8c03\u5473")}),
            cooking_step("serve", z(r"\u76db\u51fa") + dish_name, z(r"\u8c03\u5473\u540e\u76db\u51fa\u3002"), {z(r"\u76db\u51fa"), z(r"\u51fa\u9505"), z(r"\u76db\u51fa") + dish_name, z(r"\u51fa\u9505") + dish_name, z(r"\u88c5\u7897")}),
        ]
    elif dish_id in boiled:
        if dish_id == "rice":
            recipe += [
                cooking_step("rinse_rice", z(r"\u6dd8\u7c73"), z(r"\u716e\u996d\u524d\u5148\u628a\u5927\u7c73\u6dd8\u6d17\u5e72\u51c0\u3002"), {z(r"\u6dd8\u7c73"), z(r"\u6d17\u7c73"), z(r"\u6e05\u6d17\u5927\u7c73")}),
                cooking_step("add_water", z(r"\u52a0\u5165\u6e05\u6c34"), z(r"\u6dd8\u7c73\u540e\u52a0\u5165\u9002\u91cf\u6e05\u6c34\u3002"), {z(r"\u52a0\u6c34"), z(r"\u52a0\u6e05\u6c34"), z(r"\u5012\u6c34"), z(r"\u52a0\u5165\u6e05\u6c34")}),
                cooking_step("put_cooker", z(r"\u653e\u5165\u7535\u996d\u7172"), z(r"\u7c73\u548c\u6c34\u51c6\u5907\u597d\u540e\u653e\u5165\u7535\u996d\u7172\u3002"), {z(r"\u653e\u5165\u7535\u996d\u7172"), z(r"\u653e\u8fdb\u7535\u996d\u7172"), z(r"\u628a\u7c73\u653e\u5165\u7535\u996d\u7172"), z(r"\u653e\u5165\u9505\u4e2d")}),
                cooking_step("start_cooking", z(r"\u5f00\u59cb\u716e\u996d"), z(r"\u76d6\u597d\u7535\u996d\u7172\u5e76\u542f\u52a8\u716e\u996d\u3002"), {z(r"\u5f00\u59cb\u716e\u996d"), z(r"\u716e\u996d"), z(r"\u542f\u52a8\u7535\u996d\u7172"), z(r"\u6309\u4e0b\u716e\u996d\u952e")}),
                cooking_step("wait_done", z(r"\u7b49\u5f85\u7c73\u996d\u716e\u719f"), z(r"\u7b49\u5f85\u7c73\u996d\u5b8c\u5168\u716e\u719f\u518d\u6253\u5f00\u3002"), {z(r"\u7b49\u5f85\u716e\u719f"), z(r"\u7b49\u5f85\u7c73\u996d\u716e\u719f"), z(r"\u7b49\u7c73\u996d\u719f"), z(r"\u716e\u719f\u7c73\u996d")}),
                cooking_step("serve", z(r"\u76db\u51fa\u7c73\u996d"), z(r"\u7c73\u996d\u716e\u597d\u540e\u76db\u51fa\u3002"), {z(r"\u76db\u51fa\u7c73\u996d"), z(r"\u51fa\u9505\u7c73\u996d"), z(r"\u76db\u996d"), z(r"\u88c5\u7897")}),
            ]
        elif dish_id == "porridge":
            recipe += [cooking_step("rinse_rice", z(r"\u6dd8\u7c73"), z(r"\u716e\u7ca5\u524d\u5148\u6dd8\u6d17\u5927\u7c73\u3002"), {z(r"\u6dd8\u7c73"), z(r"\u6d17\u7c73")}), cooking_step("add_water", z(r"\u52a0\u5165\u8f83\u591a\u6e05\u6c34"), z(r"\u716e\u7ca5\u9700\u8981\u6bd4\u7c73\u996d\u66f4\u591a\u7684\u6c34\u3002"), {z(r"\u52a0\u6c34"), z(r"\u52a0\u5165\u6e05\u6c34"), z(r"\u52a0\u8f83\u591a\u6c34")}), cooking_step("start_boil", z(r"\u5f00\u59cb\u716e\u7ca5"), z(r"\u5f00\u706b\u628a\u7c73\u548c\u6c34\u716e\u8d77\u6765\u3002"), {z(r"\u5f00\u59cb\u716e\u7ca5"), z(r"\u716e\u7ca5")}), cooking_step("simmer", z(r"\u5c0f\u706b\u71ac\u716e"), z(r"\u8f6c\u5c0f\u706b\u6162\u6162\u71ac\u5230\u7c73\u7c92\u8f6f\u70c2\u3002"), {z(r"\u5c0f\u706b\u71ac\u716e"), z(r"\u71ac\u7ca5"), z(r"\u71ac\u716e")}), cooking_step("serve", z(r"\u76db\u51fa\u7ca5"), z(r"\u7ca5\u716e\u7a20\u540e\u76db\u51fa\u3002"), {z(r"\u76db\u51fa\u7ca5"), z(r"\u76db\u7ca5"), z(r"\u88c5\u7897")})]
        elif dish_id == "boiled_corn":
            recipe += [cooking_step("add_water", z(r"\u9505\u4e2d\u52a0\u6c34"), z(r"\u9505\u4e2d\u52a0\u5165\u80fd\u6ca1\u8fc7\u7389\u7c73\u7684\u6e05\u6c34\u3002"), {z(r"\u52a0\u6c34"), z(r"\u9505\u4e2d\u52a0\u6c34")}), cooking_step("put_corn", z(r"\u653e\u5165\u7389\u7c73"), z(r"\u628a\u7389\u7c73\u653e\u5165\u9505\u4e2d\u3002"), {z(r"\u653e\u5165\u7389\u7c73"), z(r"\u4e0b\u7389\u7c73")}), cooking_step("start_boil", z(r"\u5f00\u59cb\u716e\u7389\u7c73"), z(r"\u5f00\u706b\u628a\u7389\u7c73\u716e\u8d77\u6765\u3002"), {z(r"\u5f00\u59cb\u716e\u7389\u7c73"), z(r"\u716e\u7389\u7c73")}), cooking_step("wait_done", z(r"\u7b49\u5f85\u7389\u7c73\u716e\u719f"), z(r"\u7b49\u5f85\u7389\u7c73\u5b8c\u5168\u716e\u719f\u3002"), {z(r"\u7b49\u5f85\u716e\u719f"), z(r"\u7b49\u5f85\u7389\u7c73\u716e\u719f"), z(r"\u716e\u719f\u7389\u7c73")}), cooking_step("serve", z(r"\u635e\u51fa\u7389\u7c73"), z(r"\u716e\u719f\u540e\u635e\u51fa\u7389\u7c73\u3002"), {z(r"\u635e\u51fa\u7389\u7c73"), z(r"\u76db\u51fa\u7389\u7c73"), z(r"\u53d6\u51fa\u7389\u7c73")})]
        else:
            recipe += [cooking_step("add_water", z(r"\u9505\u4e2d\u52a0\u6c34"), z(r"\u5148\u5f80\u9505\u4e2d\u52a0\u5165\u6e05\u6c34\u3002"), {z(r"\u52a0\u6c34"), z(r"\u9505\u4e2d\u52a0\u6c34")}), cooking_step("boil_water", z(r"\u70e7\u5f00\u6e05\u6c34"), z(r"\u628a\u6c34\u70e7\u5f00\u540e\u518d\u4e0b\u9762\u3002"), {z(r"\u70e7\u6c34"), z(r"\u716e\u6c34"), z(r"\u70e7\u5f00\u6e05\u6c34")}), cooking_step("add_noodles", z(r"\u4e0b\u9762\u6761"), z(r"\u6c34\u5f00\u540e\u4e0b\u9762\u6761\u3002"), {z(r"\u4e0b\u9762\u6761"), z(r"\u52a0\u5165\u9762\u6761"), z(r"\u653e\u5165\u9762\u6761")}), cooking_step("cook_noodles", z(r"\u716e\u719f\u9762\u6761"), z(r"\u628a\u9762\u6761\u716e\u5230\u719f\u900f\u3002"), {z(r"\u716e\u9762\u6761"), z(r"\u716e\u719f\u9762\u6761"), z(r"\u716e\u719f")}), cooking_step("season", z(r"\u52a0\u76d0\u8c03\u5473"), z(r"\u9762\u6761\u719f\u540e\u52a0\u76d0\u8c03\u5473\u3002"), {z(r"\u52a0\u76d0"), z(r"\u52a0\u76d0\u8c03\u5473")}), cooking_step("serve", z(r"\u76db\u51fa") + dish_name, z(r"\u8c03\u5473\u540e\u76db\u51fa\u3002"), {z(r"\u76db\u51fa"), z(r"\u51fa\u9505"), z(r"\u76db\u51fa") + dish_name, z(r"\u88c5\u7897")})]
    elif dish_id in salads:
        if dish_id == "sandwich":
            recipe += [cooking_step("wash_vegetable", z(r"\u6e05\u6d17\u9752\u83dc"), z(r"\u5148\u628a\u5939\u5165\u4e09\u660e\u6cbb\u7684\u9752\u83dc\u6d17\u5e72\u51c0\u3002"), {z(r"\u6d17\u9752\u83dc"), z(r"\u6e05\u6d17\u9752\u83dc")}), cooking_step("fry_or_prepare_egg", z(r"\u714e\u719f\u9e21\u86cb"), z(r"\u628a\u9e21\u86cb\u714e\u719f\u540e\u518d\u5939\u5165\u9762\u5305\u3002"), {z(r"\u714e\u9e21\u86cb"), z(r"\u714e\u719f\u9e21\u86cb"), z(r"\u4e0b\u6cb9\u714e\u86cb"), z(r"\u714e\u86cb")}), cooking_step("slice_bread", z(r"\u6446\u653e\u9762\u5305"), z(r"\u628a\u9762\u5305\u7247\u6446\u597d\u3002"), {z(r"\u6446\u653e\u9762\u5305"), z(r"\u653e\u597d\u9762\u5305"), z(r"\u51c6\u5907\u9762\u5305")}), cooking_step("add_fillings", z(r"\u5939\u5165\u9e21\u86cb\u548c\u9752\u83dc"), z(r"\u628a\u9e21\u86cb\u548c\u9752\u83dc\u5939\u5165\u9762\u5305\u4e2d\u3002"), {z(r"\u5939\u5165\u9e21\u86cb\u548c\u9752\u83dc"), z(r"\u52a0\u5165\u9e21\u86cb\u548c\u9752\u83dc"), z(r"\u5939\u83dc")}), cooking_step("plate", z(r"\u88c5\u76d8\u4e09\u660e\u6cbb"), z(r"\u5939\u597d\u540e\u5207\u5f00\u6216\u88c5\u76d8\u3002"), {z(r"\u88c5\u76d8"), z(r"\u88c5\u76d8\u4e09\u660e\u6cbb"), z(r"\u5207\u5f00\u4e09\u660e\u6cbb")})]
        else:
            item = cucumber if dish_id == "cucumber_salad" else noodles
            recipe += [cooking_step("wash", z(r"\u6e05\u6d17") + item, z(r"\u5148\u628a") + item + z(r"\u5904\u7406\u5e72\u51c0\u3002"), {z(r"\u6d17") + item, z(r"\u6e05\u6d17") + item}), cooking_step("cut", z(r"\u5207\u914d") + item, z(r"\u628a") + item + z(r"\u5207\u6210\u9002\u5408\u51c9\u62cc\u7684\u5f62\u72b6\u3002"), {z(r"\u5207") + item, z(r"\u5207\u914d") + item}), cooking_step("add_seasoning", z(r"\u52a0\u5165\u8c03\u6599"), z(r"\u52a0\u5165\u76d0\u7b49\u8c03\u6599\u3002"), {z(r"\u52a0\u5165\u8c03\u6599"), z(r"\u52a0\u76d0"), z(r"\u52a0\u8c03\u6599"), z(r"\u8c03\u5473")}), cooking_step("mix", z(r"\u62cc\u5300"), z(r"\u628a\u98df\u6750\u548c\u8c03\u6599\u5145\u5206\u62cc\u5300\u3002"), {z(r"\u62cc\u5300"), z(r"\u6405\u62cc"), z(r"\u62cc\u9762"), z(r"\u62cc\u9ec4\u74dc")}), cooking_step("plate", z(r"\u88c5\u76d8") + dish_name, z(r"\u62cc\u597d\u540e\u88c5\u76d8\u3002"), {z(r"\u88c5\u76d8"), z(r"\u88c5\u76d8") + dish_name, z(r"\u76db\u51fa") + dish_name})]
    elif dish_id == "potato_chicken":
        recipe += [cooking_step("cut_potato", z(r"\u5207\u571f\u8c46"), z(r"\u5148\u628a\u571f\u8c46\u5207\u5757\u3002"), {z(r"\u5207\u571f\u8c46"), z(r"\u571f\u8c46\u5207\u5757")}), cooking_step("cut_chicken", z(r"\u5207\u9e21\u8089"), z(r"\u628a\u9e21\u8089\u5207\u6210\u9002\u53e3\u5927\u5c0f\u3002"), {z(r"\u5207\u9e21\u8089"), z(r"\u9e21\u8089\u5207\u5757")}), cooking_step("add_water", z(r"\u9505\u4e2d\u52a0\u6c34"), z(r"\u9505\u4e2d\u52a0\u5165\u6e05\u6c34\u51c6\u5907\u7096\u716e\u3002"), {z(r"\u52a0\u6c34"), z(r"\u9505\u4e2d\u52a0\u6c34")}), cooking_step("add_ingredients", z(r"\u4e0b\u571f\u8c46\u548c\u9e21\u8089"), z(r"\u628a\u571f\u8c46\u548c\u9e21\u8089\u653e\u5165\u9505\u4e2d\u3002"), {z(r"\u4e0b\u571f\u8c46\u548c\u9e21\u8089"), z(r"\u52a0\u5165\u571f\u8c46\u548c\u9e21\u8089"), z(r"\u653e\u5165\u571f\u8c46\u548c\u9e21\u8089")}), cooking_step("start_stew", z(r"\u5f00\u59cb\u7096\u716e"), z(r"\u5f00\u706b\u7096\u716e\u571f\u8c46\u9e21\u8089\u3002"), {z(r"\u5f00\u59cb\u7096"), z(r"\u7096\u716e"), z(r"\u5f00\u59cb\u7096\u716e")}), cooking_step("wait_done", z(r"\u7b49\u5f85\u7096\u719f"), z(r"\u7b49\u5f85\u9e21\u8089\u719f\u900f\u3001\u571f\u8c46\u53d8\u8f6f\u3002"), {z(r"\u7b49\u5f85\u7096\u719f"), z(r"\u7096\u719f"), z(r"\u7b49\u5f85\u719f\u900f")}), cooking_step("season", z(r"\u52a0\u76d0\u8c03\u5473"), z(r"\u51fa\u9505\u524d\u52a0\u76d0\u8c03\u5473\u3002"), {z(r"\u52a0\u76d0"), z(r"\u52a0\u76d0\u8c03\u5473")}), cooking_step("serve", z(r"\u76db\u51fa") + dish_name, z(r"\u7096\u597d\u540e\u76db\u51fa\u3002"), {z(r"\u76db\u51fa"), z(r"\u51fa\u9505"), z(r"\u76db\u51fa") + dish_name})]
    elif dish_id in stir_fry:
        prep = []
        if "tomato" in target["ingredients"]:
            prep.append(cooking_step("cut_tomato", z(r"\u5207\u756a\u8304"), z(r"\u5148\u628a\u756a\u8304\u6d17\u51c0\u5207\u5757\u3002"), {z(r"\u5207\u756a\u8304"), z(r"\u5207\u897f\u7ea2\u67ff")}))
        if "potato" in target["ingredients"]:
            prep.append(cooking_step("cut_potato", z(r"\u5207\u571f\u8c46"), z(r"\u5148\u628a\u571f\u8c46\u5207\u6210\u4e1d\u6216\u5757\u3002"), {z(r"\u5207\u571f\u8c46"), z(r"\u5207\u571f\u8c46\u4e1d")}))
        if "carrot" in target["ingredients"]:
            prep.append(cooking_step("cut_carrot", z(r"\u5207\u80e1\u841d\u535c"), z(r"\u5148\u628a\u80e1\u841d\u535c\u5207\u597d\u3002"), {z(r"\u5207\u80e1\u841d\u535c"), z(r"\u5207\u80e1\u841d\u535c\u7247")}))
        if "green vegetable" in target["ingredients"]:
            prep.append(cooking_step("wash_vegetable", z(r"\u6d17\u9752\u83dc"), z(r"\u9752\u83dc\u4e0b\u9505\u524d\u8981\u6d17\u5e72\u51c0\u3002"), {z(r"\u6d17\u9752\u83dc"), z(r"\u6e05\u6d17\u9752\u83dc")}))
        if "tofu" in target["ingredients"]:
            prep.append(cooking_step("cut_tofu", z(r"\u5207\u8c46\u8150"), z(r"\u5148\u628a\u8c46\u8150\u5207\u5757\u3002"), {z(r"\u5207\u8c46\u8150"), z(r"\u8c46\u8150\u5207\u5757")}))
        if "egg" in target["ingredients"]:
            prep.append(cooking_step("beat_egg", z(r"\u6253\u6563\u9e21\u86cb"), z(r"\u5148\u628a\u9e21\u86cb\u6253\u6563\u5907\u7528\u3002"), {z(r"\u6253\u9e21\u86cb"), z(r"\u6253\u86cb"), z(r"\u6405\u6253\u9e21\u86cb")}))
        recipe += prep + [cooking_step("heat_pan", z(r"\u70ed\u9505"), z(r"\u5148\u628a\u9505\u70e7\u70ed\u3002"), {z(r"\u70ed\u9505"), z(r"\u70e7\u70ed\u9505")}), cooking_step("add_oil", z(r"\u5012\u6cb9"), z(r"\u9505\u70ed\u540e\u5012\u5165\u98df\u7528\u6cb9\u3002"), {z(r"\u5012\u6cb9"), z(r"\u5012\u98df\u7528\u6cb9"), z(r"\u4e0b\u6cb9")}), cooking_step("add_main", z(r"\u4e0b") + main, z(r"\u6cb9\u70ed\u540e\u653e\u5165") + main + z(r"\u3002"), {z(r"\u4e0b") + main, z(r"\u52a0\u5165") + main, z(r"\u653e\u5165") + main}), cooking_step("stir_fry", z(r"\u7ffb\u7092"), z(r"\u6301\u7eed\u7ffb\u7092\u8ba9\u98df\u6750\u53d7\u70ed\u5747\u5300\u3002"), {z(r"\u7ffb\u7092"), z(r"\u7ffb\u7092") + main, z(r"\u7092\u5300")}), cooking_step("season", z(r"\u52a0\u76d0\u8c03\u5473"), z(r"\u98df\u6750\u5feb\u719f\u65f6\u52a0\u5165\u76d0\u8c03\u5473\u3002"), {z(r"\u52a0\u76d0"), z(r"\u52a0\u76d0\u8c03\u5473"), z(r"\u653e\u76d0"), z(r"\u8c03\u5473")}), cooking_step("plate", z(r"\u88c5\u76d8") + dish_name, z(r"\u7092\u597d\u540e\u5173\u706b\u88c5\u76d8\u3002"), {z(r"\u88c5\u76d8"), z(r"\u76db\u51fa"), z(r"\u51fa\u9505"), z(r"\u88c5\u76d8") + dish_name, z(r"\u76db\u51fa") + dish_name})]
    else:
        recipe += [cooking_step("prepare", z(r"\u5904\u7406") + main, z(r"\u5148\u628a\u4e3b\u8981\u98df\u6750\u6e05\u6d17\u5207\u914d\u597d\u3002"), {z(r"\u5904\u7406") + main, z(r"\u51c6\u5907") + main}), cooking_step("heat_pan", z(r"\u70ed\u9505"), z(r"\u5148\u628a\u9505\u70e7\u70ed\u3002"), {z(r"\u70ed\u9505")}), cooking_step("add_oil", z(r"\u5012\u6cb9"), z(r"\u9505\u70ed\u540e\u5012\u5165\u98df\u7528\u6cb9\u3002"), {z(r"\u5012\u6cb9"), z(r"\u4e0b\u6cb9")}), cooking_step("add_main", z(r"\u4e0b") + main, z(r"\u6cb9\u70ed\u540e\u653e\u5165") + main + z(r"\u3002"), {z(r"\u4e0b") + main}), cooking_step("stir_fry", z(r"\u7ffb\u7092"), z(r"\u6301\u7eed\u7ffb\u7092\u81f3\u719f\u3002"), {z(r"\u7ffb\u7092")}), cooking_step("season", z(r"\u52a0\u76d0\u8c03\u5473"), z(r"\u98df\u6750\u719f\u540e\u52a0\u76d0\u8c03\u5473\u3002"), {z(r"\u52a0\u76d0")}), cooking_step("plate", z(r"\u88c5\u76d8") + dish_name, z(r"\u505a\u597d\u540e\u88c5\u76d8\u3002"), {z(r"\u88c5\u76d8"), z(r"\u76db\u51fa"), z(r"\u51fa\u9505")})]
    return recipe


def cooking_step_state(session, dish_id):
    return session.setdefault("cookingSteps", {}).setdefault(dish_id, {"index": 0, "completed": []})


def has_inventory_items(session, items):
    names = set(textworld_inventory_names(session["tw_state"]))
    return all(item in names for item in items)


def cooking_target_completed(session, target):
    recipe = cooking_recipe(target)
    state = cooking_step_state(session, target["id"])
    return has_inventory_items(session, target["ingredients"]) and state["index"] >= len(recipe)


def active_cooking_targets(session):
    if session.get("scenario") != "cooking":
        return []
    completed = session.get("completedTargetIds", set())
    return [target for target in session["world"]["targets"] if target["id"] not in completed]


def cooking_next_step(session, target):
    recipe = cooking_recipe(target)
    state = cooking_step_state(session, target["id"])
    if not has_inventory_items(session, target["ingredients"]):
        return recipe[0]
    if state["index"] < 1:
        return recipe[1] if len(recipe) > 1 else None
    return recipe[state["index"]] if state["index"] < len(recipe) else None


def cooking_step_tip(session, target=None):
    if session.get("scenario") != "cooking":
        return ""
    target = target or next((item for item in active_cooking_targets(session) if cooking_next_step(session, item)), None)
    if not target:
        return "烹制菜品已完成，可以继续完成其它目标。"
    step = cooking_next_step(session, target)
    if not step:
        return f"{target['name']}已完成，可以继续完成其它目标。"
    return f"{target['name']}下一步：{step['name']}。{step['tip']}"



def target_step_state(session, target_id):
    if session.get("scenario") == "cooking":
        return cooking_step_state(session, target_id)
    return session.setdefault("targetSteps", {}).setdefault(target_id, {"index": 0, "completed": []})


def command_variants(text):
    return {text, text.replace(" ", "")}


def named_step(step_id, name, tip=None, commands=None):
    return {"id": step_id, "name": name, "tip": tip or name, "commands": set(commands or command_variants(name))}


def fire_steps(target):
    names = FIRE_SPECIAL_STEPS.get(target["id"]) or [f"观察{target['name']}", f"判断{target['name']}风险", target.get("action", f"处理{target['name']}"), f"确认{target['name']}已排除"]
    steps = []
    for index, name in enumerate(names):
        commands = command_variants(name) | {name.replace(target["name"], "隐患")}
        if index == 0:
            commands |= {f"查看{target['name']}", f"观察{target['name']}"}
        if index == len(names) - 1:
            commands |= {f"处理{target['name']}", f"修复{target['name']}", f"排除{target['name']}"}
        steps.append(named_step(f"fire_{index}", name, f"完成“{name}”后再进入下一步。", commands))
    return steps


def garbage_steps(target):
    steps = [named_step("take", f"拿起{target['name']}", f"先拿起{target['name']}，再判断它属于哪类垃圾。", {f"拿{target['name']}", f"拿起{target['name']}", f"拾取{target['name']}"})]
    preprocess = GARBAGE_PREPROCESS.get(target["id"])
    if preprocess:
        steps.append(named_step("preprocess", preprocess, "复合或可回收物投放前要先预处理。", command_variants(preprocess)))
    steps.append(named_step("judge", f"判断为{target['category']}", f"{target['tip']}", {f"判断{target['name']}是{target['category']}", f"判断{target['category']}", f"分类{target['name']}"}))
    steps.append(named_step("drop", f"投放到{target['category']}", f"最后把{target['name']}投放到{target['category']}桶。", {f"投放{target['name']}到{target['category']}", f"扔{target['name']}到{target['category']}", f"放入{target['category']}桶", f"投放到{target['category']}"}))
    return steps


def target_steps(session, target):
    if session["scenario"] == "cooking":
        return cooking_recipe(target)
    if session["scenario"] == "fire_safety":
        return fire_steps(target)
    if session["scenario"] == "garbage_sorting":
        return garbage_steps(target)
    return []


def target_has_required_item(session, target):
    if session["scenario"] == "cooking":
        return has_inventory_items(session, target["ingredients"])
    if session["scenario"] == "fire_safety":
        return target["english"] in set(textworld_inventory_names(session["tw_state"]))
    if session["scenario"] == "garbage_sorting":
        return True
    return False


def target_completed_by_steps(session, target):
    steps = target_steps(session, target)
    state = target_step_state(session, target["id"])
    return bool(steps) and state["index"] >= len(steps)


def active_targets(session):
    completed = session.get("completedTargetIds", set())
    return [target for target in session["world"]["targets"] if target["id"] not in completed]


def next_target_step(session, target):
    steps = target_steps(session, target)
    if not steps:
        return None
    state = target_step_state(session, target["id"])
    return steps[state["index"]] if state["index"] < len(steps) else None


def step_tip(session, target=None):
    target = target or next((item for item in active_targets(session) if next_target_step(session, item)), None)
    if not target:
        return "所有目标已完成，可以开始新游戏继续练习。"
    step = next_target_step(session, target)
    if not step:
        return f"{target['name']}已完成，可以继续处理其它目标。"
    return f"{target['name']}下一步：{step['name']}。{step['tip']}"


def is_scene_step_command(session, compact):
    if session.get("scenario") == "cooking":
        return is_cooking_step_command(session, compact)
    if session.get("scenario") not in {"fire_safety", "garbage_sorting"}:
        return False
    return any(compact in step["commands"] for target in active_targets(session) for step in target_steps(session, target))


def target_for_step_command(session, compact):
    matches = []
    for target in active_targets(session):
        steps = target_steps(session, target)
        for index, step in enumerate(steps):
            if compact in step["commands"]:
                matches.append((target, index, step))
    if len(matches) == 1:
        return matches[0]
    for target in active_targets(session):
        if target["name"] in compact or target.get("category", "") in compact:
            step = next_target_step(session, target)
            if step:
                return target, target_steps(session, target).index(step), step
    target = next((item for item in active_targets(session) if next_target_step(session, item)), None)
    if target:
        step = next_target_step(session, target)
        return target, target_steps(session, target).index(step), step
    return None, None, None


def handle_target_step(session, command):
    if session["scenario"] == "cooking":
        return handle_cooking_step(session, command)
    action_label = "处理隐患" if session["scenario"] == "fire_safety" else "垃圾分类"
    compact = command.replace(" ", "")
    target, matched_index, _matched_step = target_for_step_command(session, compact)
    if not target:
        return {"ok": False, "action": action_label, "scoreDelta": 0, "done": False, "feedback": "没有找到对应目标，请先查看当前建议指令。", "teachingTip": step_tip(session)}
    steps = target_steps(session, target)
    state = target_step_state(session, target["id"])
    expected = steps[state["index"]] if state["index"] < len(steps) else None
    if expected is None:
        return {"ok": True, "action": action_label, "scoreDelta": 0, "done": True, "feedback": f"{target['name']}已经完成。", "teachingTip": step_tip(session)}
    actual_index = next((index for index, step in enumerate(steps) if compact in step["commands"]), matched_index)
    if actual_index is None or compact not in steps[actual_index]["commands"]:
        session["mistakes"] += 1
        return {"ok": False, "action": action_label, "scoreDelta": 0, "done": False, "feedback": f"这个动作暂时不适合{target['name']}，当前应执行：{expected['name']}。", "teachingTip": expected["tip"]}
    if actual_index != state["index"]:
        session["mistakes"] += 1
        return {"ok": False, "action": action_label, "scoreDelta": 0, "done": False, "feedback": f"顺序不对，请先完成：{expected['name']}。", "teachingTip": expected["tip"]}
    state["completed"].append(expected["id"])
    state["index"] += 1
    done_target = target_completed_by_steps(session, target)
    next_tip = step_tip(session)
    feedback = f"已完成：{expected['name']}。" + (target.get("successFeedback", f"{target['name']}完成！") if done_target else "")
    return {"ok": True, "action": action_label, "scoreDelta": 1 if done_target else 0, "done": len(completed_target_ids(session)) == len(session["world"]["targets"]), "feedback": feedback, "teachingTip": next_tip}


def progress(session):
    completed = len(completed_target_ids(session))
    total = len(session["world"]["targets"])
    score = int(getattr(session["tw_state"], "score", 0) or 0)
    payload = {"completed": completed, "total": total, "percent": round(completed / total * 100) if total else 100, "score": score, "mistakes": session["mistakes"], "targetProgress": {}}
    next_target = next((target for target in active_targets(session) if next_target_step(session, target)), None)
    if next_target:
        step = next_target_step(session, next_target)
        state = target_step_state(session, next_target["id"])
        steps = target_steps(session, next_target)
        payload["currentStep"] = f"{next_target['name']}：{step['name']}"
        payload["stepCompleted"] = min(state["index"], len(steps))
        payload["stepTotal"] = len(steps)
    for target in session["world"]["targets"]:
        steps = target_steps(session, target)
        state = target_step_state(session, target["id"])
        current_step = steps[state["index"]] if state["index"] < len(steps) else None
        payload["targetProgress"][target["id"]] = {"currentStep": current_step["id"] if current_step else None, "currentStepName": current_step["name"] if current_step else "已完成", "completedSteps": list(state["completed"]), "stepIndex": min(state["index"], len(steps)), "stepTotal": len(steps)}
    return payload


def target_summary(session):
    completed = completed_target_ids(session)
    summary = []
    for target in session["world"]["targets"]:
        step = next_target_step(session, target)
        item = {"id": target["id"], "name": target["name"], "type": target["type"], "completed": target["id"] in completed, "knowledgePoint": target.get("knowledgePoint", target.get("tip", "")), "currentStep": step["name"] if step else None, "steps": [{"id": step_item["id"], "name": step_item["name"], "tip": step_item["tip"]} for step_item in target_steps(session, target)]}
        if target["id"] not in completed and step:
            item["displayName"] = f"{target['name']}：{step['name']}"
        summary.append(item)
    return summary


def build_map(session):
    completed = completed_target_ids(session)
    rooms = []
    for room in session["world"]["rooms"]:
        target_count = sum(1 for item in room.get("items", []) if item["id"] not in completed)
        rooms.append({"id": room["id"], "name": room["name"], "x": room["x"], "y": room["y"], "current": room["id"] == session["currentRoom"], "visited": room["id"] in session["visitedRooms"], "targetCount": target_count})
    return {"rooms": rooms, "nodes": rooms, "connections": session["world"]["connections"], "edges": session["world"]["connections"]}


def clean_engine_feedback(feedback):
    text = str(feedback or "").strip()
    if not text or "To get text observation" in text:
        return ""
    if text == "Invalid command.":
        return "这个中文指令暂时无法执行，请换一种说法或先查看房间。"
    if any(text.startswith(prefix) for prefix in ("食材", "顺序", "这个烹饪", "已完成", "番茄炒蛋")):
        return text
    return ""


def visible_command_suggestions(session):
    room = get_room(session, session["currentRoom"])
    suggestions = ["查看房间", "查看背包"]
    for direction in room.get("exits", {}):
        suggestions.append(f"前往{DIRECTION_LABELS[direction]}边")
    completed = completed_target_ids(session)
    for item in room.get("items", []):
        if item["id"] in completed:
            continue
        if session["scenario"] == "cooking":
            target = next((target for target in session["world"]["targets"] if target["id"] == item["id"]), None)
            if target:
                for ingredient in target["ingredients"]:
                    suggestions.append(f"拿{EN_TO_CN.get(ingredient, ingredient)}")
                continue
        if session["scenario"] == "fire_safety":
            suggestions.append(f"处理{item['name']}")
        elif session["scenario"] == "garbage_sorting":
            target = next((target for target in session["world"]["targets"] if target["id"] == item["id"]), None)
            if target:
                suggestions.append(f"投放{item['name']}到{target['category']}")
            else:
                suggestions.append(f"拿{item['name']}")
        else:
            suggestions.append(f"拿{item['name']}")
    if session["scenario"] in {"cooking", "fire_safety", "garbage_sorting"}:
        for target in active_targets(session):
            step = next_target_step(session, target)
            if step:
                suggestions.append(step["name"])
    return suggestions[:8]


def describe_room(session, tw_feedback=None):
    room = get_room(session, session["currentRoom"])
    exits = "、".join(f"{DIRECTION_LABELS[direction]}->{get_room(session, target)['name']}" for direction, target in room.get("exits", {}).items()) or "无"
    completed = completed_target_ids(session)
    items = [item["name"] for item in room.get("items", []) if item["id"] not in completed]
    lines = [f"{room['name']}：{room['description']}", f"出口：{exits}"]
    lines.append("可见物品/目标：" + ("、".join(items) if items else "无"))
    cleaned = clean_engine_feedback(tw_feedback)
    if cleaned:
        lines.append("\n操作结果：" + cleaned)
    return "\n".join(lines)


def inventory_log_message(session):
    inventory = inventory_display(session)
    return "背包中有：" + "、".join(inventory) if inventory else "背包为空"


def command_log_message(session, action, result=None, feedback=""):
    result = result or {}
    if action == "inventory":
        return inventory_log_message(session)
    if action == "look":
        return describe_room(session)
    if action == "move":
        return describe_room(session, "已移动到当前房间。" if result.get("ok", True) else feedback)
    if action == "take":
        cleaned = clean_engine_feedback(feedback)
        if result.get("ok") is False:
            return cleaned or "没有拾取成功，请先查看房间确认物品位置。"
        return cleaned or "已拾取物品。" + inventory_log_message(session)
    if action == "cook_collect":
        cleaned = clean_engine_feedback(feedback)
        if result.get("ok") is False:
            return cleaned or "没有备齐食材，请先查看房间确认食材位置。"
        return cleaned or "已备齐食材。" + inventory_log_message(session)
    if action == "textworld":
        cleaned = clean_engine_feedback(feedback)
        return cleaned or ("操作已执行。" if result.get("ok", True) else "这个指令暂时无法执行，请换一种说法或先查看房间。")
    return clean_engine_feedback(feedback) or result.get("feedback") or "操作已执行。"


def response_payload(session, response, last_action_result=None, teaching_tip=None, log_message=None):
    completed = completed_target_ids(session)
    done = len(completed) == len(session["world"]["targets"])
    session["done"] = done
    return {
        "response": response,
        "logMessage": log_message if log_message is not None else response,
        "currentRoom": get_room(session, session["currentRoom"])["name"],
        "currentRoomId": session["currentRoom"],
        "inventory": inventory_display(session),
        "progress": progress(session),
        "lastActionResult": last_action_result or {},
        "teachingTip": teaching_tip or "可以使用中文指令查看、移动、拾取或完成当前目标。",
        "done": done,
        "map": build_map(session),
        "targets": target_summary(session),
        "admissibleCommands": visible_command_suggestions(session),
        "engine": session["engine"],
    }


def inventory_display(session):
    names = textworld_inventory_names(session["tw_state"])
    display = []
    for name in names:
        display.append(next((cn for cn, en in CN_TO_EN.items() if en == name and cn not in CATEGORY_TO_BIN), name))
    return display


def command_help(session):
    lines = [
        "你可以直接输入中文指令：查看房间、查看背包、前往东边、拿番茄。",
        "场景动作示例：处理超负荷插线板、投放苹果核到厨余垃圾。",
    ]
    if session.get("scenario") == "cooking":
        for target in session["world"]["targets"]:
            lines.append(f"{target['name']}步骤：" + " → ".join(step["name"] for step in cooking_recipe(target)))
    lines.append("当前建议：" + "；".join(visible_command_suggestions(session)))
    return "\n".join(lines)


def translate_command(session, command):
    raw = command.strip()
    compact = raw.replace(" ", "")
    normalized, words = split_command(raw)
    verb = words[0] if words else ""
    if normalized in LOOK_COMMANDS:
        return "look", "look"
    if normalized in INVENTORY_COMMANDS:
        return "inventory", "inventory"
    direction = extract_direction(raw, words)
    if verb in MOVE_VERBS or normalized in DIRECTION_ALIASES or direction:
        return f"go {direction}", "move"
    if session["scenario"] == "cooking" and is_cooking_step_command(session, compact):
        target, matched_index, _matched_step = cooking_target_for_command(session, compact)
        if target and matched_index == 0:
            return target["name"], "cook_collect"
        return raw, "cook_step"
    take_target = extract_take_keyword(raw, words)
    if session["scenario"] == "garbage_sorting" and take_target:
        target = find_target_in_text(session, raw)
        if target:
            return raw, "sort_step"
    if take_target:
        return "take " + translate_name(take_target), "take"
    if is_scene_step_command(session, compact):
        return raw, {"cooking": "cook_step", "fire_safety": "fix_step", "garbage_sorting": "sort_step"}.get(session["scenario"], "textworld")
    if session["scenario"] == "cooking" and (verb in COOK_VERBS or starts_with_any(compact, COOK_VERBS)):
        target = find_target_in_text(session, raw)
        if target:
            return raw, "cook_step"
    if session["scenario"] == "fire_safety" and (verb in FIX_VERBS or starts_with_any(compact, FIX_VERBS)):
        target = find_target_in_text(session, raw)
        if target:
            return raw, "fix_step"
    if session["scenario"] == "garbage_sorting" and (verb in SORT_VERBS or starts_with_any(compact, SORT_VERBS)):
        target = find_target_in_text(session, raw)
        if target:
            return raw, "sort_step"
    return raw, "textworld"


def is_cooking_step_command(session, compact):
    if session.get("scenario") != "cooking":
        return False
    if any(compact in step["commands"] for target in session["world"]["targets"] for step in cooking_recipe(target)):
        return True
    return starts_with_any(compact, COOKING_STEP_VERBS)


def cooking_target_for_command(session, compact):
    matches = []
    for target in active_cooking_targets(session):
        recipe = cooking_recipe(target)
        for index, step in enumerate(recipe):
            if compact in step["commands"]:
                matches.append((target, index, step))
    if len(matches) == 1:
        return matches[0]
    for target in active_cooking_targets(session):
        if target["name"] in compact or target["id"] in compact:
            step = cooking_next_step(session, target)
            if step:
                return target, cooking_recipe(target).index(step), step
    target = next((item for item in active_cooking_targets(session) if cooking_next_step(session, item)), None)
    if target:
        step = cooking_next_step(session, target)
        return target, cooking_recipe(target).index(step), step
    return None, None, None


def handle_cooking_step(session, command):
    compact = command.replace(" ", "")
    target, matched_index, _matched_step = cooking_target_for_command(session, compact)
    if not target:
        return {"ok": False, "action": "烹饪步骤", "scoreDelta": 0, "done": False, "feedback": "当前没有需要继续烹制的菜品。", "teachingTip": "可以查看目标进度确认下一道菜。"}
    recipe = cooking_recipe(target)
    state = cooking_step_state(session, target["id"])
    if state["index"] == 0 and matched_index == 0:
        state["completed"].append(recipe[0]["id"])
        state["index"] = 1
        next_tip = cooking_step_tip(session, target)
        return {"ok": True, "action": "备齐食材", "scoreDelta": 0, "done": False, "feedback": f"已备齐{target['name']}需要的食材。", "teachingTip": next_tip}
    if not has_inventory_items(session, target["ingredients"]):
        missing = [EN_TO_CN.get(item, item) for item in target["ingredients"] if item not in set(textworld_inventory_names(session["tw_state"]))]
        session["mistakes"] += 1
        return {"ok": False, "action": "烹饪步骤", "scoreDelta": 0, "done": False, "feedback": f"食材还没备齐，请先拿：{'、'.join(missing)}。", "teachingTip": cooking_step_tip(session, target)}
    if state["index"] < 1:
        state["index"] = 1
    expected = recipe[state["index"]] if state["index"] < len(recipe) else None
    actual_index = next((index for index, step in enumerate(recipe[1:], start=1) if compact in step["commands"]), matched_index)
    if expected is None:
        return {"ok": True, "action": "烹饪步骤", "scoreDelta": 0, "done": True, "feedback": f"{target['name']}已经完成。", "teachingTip": cooking_step_tip(session)}
    if actual_index is None or compact not in recipe[actual_index]["commands"]:
        session["mistakes"] += 1
        return {"ok": False, "action": "烹饪步骤", "scoreDelta": 0, "done": False, "feedback": f"这个烹饪动作暂时不适合{target['name']}。当前应执行：{expected['name']}。", "teachingTip": expected["tip"]}
    if actual_index != state["index"]:
        session["mistakes"] += 1
        return {"ok": False, "action": "烹饪步骤", "scoreDelta": 0, "done": False, "feedback": f"顺序不对。当前应先完成：{expected['name']}。", "teachingTip": expected["tip"]}
    state["completed"].append(expected["id"])
    state["index"] += 1
    done = cooking_target_completed(session, target)
    next_tip = cooking_step_tip(session)
    feedback = f"已完成：{expected['name']}。" + (f"{target['name']}完成！" if done else "")
    return {"ok": True, "action": "烹饪步骤", "scoreDelta": 1 if done else 0, "done": len(completed_target_ids(session)) == len(session["world"]["targets"]), "feedback": feedback, "teachingTip": next_tip}


def command_sequence_for(session, tw_command, action):
    commands = [tw_command]
    if action == "cook_collect":
        target = find_target_in_text(session, tw_command)
        commands = collect_command_sequence(session, target) if target else [tw_command]
    if action == "sort" and tw_command not in (getattr(session["tw_state"], "admissible_commands", []) or []):
        item = extract_insert_item(tw_command)
        if item:
            commands.insert(0, f"take {item}")
    return commands


def route_between(session, start_room_id, target_room_id):
    if start_room_id == target_room_id:
        return []
    queue = [(start_room_id, [])]
    visited = {start_room_id}
    while queue:
        room_id, path = queue.pop(0)
        room = get_room(session, room_id)
        for direction, next_room_id in room.get("exits", {}).items():
            if next_room_id in visited:
                continue
            next_path = path + [direction]
            if next_room_id == target_room_id:
                return next_path
            visited.add(next_room_id)
            queue.append((next_room_id, next_path))
    return []


def collect_command_sequence(session, target):
    commands = []
    current_room_id = session["currentRoom"]
    for ingredient in target.get("ingredients", []):
        holder_room = ingredient_holder_room(session, ingredient, target)
        if holder_room:
            for direction in route_between(session, current_room_id, holder_room["id"]):
                commands.append(f"go {direction}")
                current_room_id = get_room(session, current_room_id)["exits"][direction]
        commands.append(f"take {ingredient}")
    return commands or [target["name"]]


def ingredient_holder_room(session, ingredient, fallback_target):
    for target in session["world"]["targets"]:
        if ingredient not in target.get("ingredients", []):
            continue
        room = next((room for room in session["world"]["rooms"] if any(item.get("id") == target["id"] for item in room.get("items", []))), None)
        if room:
            return room
    return next((room for room in session["world"]["rooms"] if any(item.get("id") == fallback_target["id"] for item in room.get("items", []))), None)


def starts_with_any(text, verbs):
    return any(text.startswith(verb) for verb in verbs)


def extract_insert_item(command):
    match = re.match(r"insert (.+) into (.+)", command)
    return match.group(1) if match else ""


def extract_direction(raw, words):
    joined = "".join(words)
    for token in [joined, *words]:
        if token in DIRECTION_ALIASES:
            return DIRECTION_ALIASES[token]
        if token in OPPOSITE:
            return token
    compact = raw.replace(" ", "")
    for chinese, english in DIRECTION_ALIASES.items():
        if re.fullmatch(r"[a-z]", chinese):
            continue
        if chinese in compact:
            return english
    return ""


def extract_take_keyword(raw, words):
    if not words:
        return ""
    if words[0] in TAKE_VERBS:
        return raw.replace(words[0], "", 1).strip()
    compact = raw.replace(" ", "")
    for verb in sorted(TAKE_VERBS, key=len, reverse=True):
        if compact.startswith(verb):
            return compact[len(verb):]
    return ""


def translate_name(text):
    raw = str(text or "").strip()
    for cn, en in sorted(CN_TO_EN.items(), key=lambda pair: len(pair[0]), reverse=True):
        if cn in raw:
            return en
    return raw.lower().replace("_", " ")


def find_target_in_text(session, text):
    normalized_text = normalize(text)
    for target in session["world"]["targets"]:
        values = [target["id"], target["name"], target.get("english", ""), target.get("category", "")]
        if any(value and (normalize(value) in normalized_text or value in text) for value in values):
            return target
    return None


def apply_command_side_effects(session, action, tw_command, previous_commands, previous_score, score, done):
    ok = score > previous_score or tw_command in previous_commands or action in {"look", "inventory", "cook_collect"}
    if tw_command == "Invalid command.":
        ok = False
    if score <= previous_score and action not in {"look", "inventory", "move", "take", "textworld", "cook_collect"}:
        pass
    if action == "move" and ok:
        direction = tw_command.split(" ", 1)[1]
        current = get_room(session, session["currentRoom"])
        if direction in current.get("exits", {}):
            session["currentRoom"] = current["exits"][direction]
            session["visitedRooms"].add(session["currentRoom"])
    if action == "cook_collect":
        target = find_target_in_text(session, tw_command)
        if target:
            current_room_id = session["currentRoom"]
            for ingredient in target.get("ingredients", []):
                holder_room = ingredient_holder_room(session, ingredient, target)
                if not holder_room:
                    continue
                for direction in route_between(session, current_room_id, holder_room["id"]):
                    current_room_id = get_room(session, current_room_id)["exits"][direction]
                    session["visitedRooms"].add(current_room_id)
            session["currentRoom"] = current_room_id
            if has_inventory_items(session, target["ingredients"]):
                state = cooking_step_state(session, target["id"])
                if state["index"] == 0:
                    state["completed"].append(cooking_recipe(target)[0]["id"])
                    state["index"] = 1
            else:
                ok = False
    if score == previous_score and action not in {"look", "inventory", "move", "take", "textworld", "cook_collect"}:
        session["mistakes"] += 1
    wrapped_done = len(completed_target_ids(session)) == len(session["world"]["targets"])
    return {"ok": ok, "action": ACTION_LABELS.get(action, "\u6267\u884c"), "scoreDelta": score - previous_score, "done": wrapped_done}


def teaching_tip(session, action, result):
    if action == "look":
        return "观察房间能发现可拾取物品、隐患或垃圾桶。"
    if action == "move":
        return "已移动到相邻房间，地图会同步标记当前位置。"
    if action == "take":
        if session.get("scenario") in {"cooking", "fire_safety", "garbage_sorting"}:
            return step_tip(session)
        return "已经拾取成功，可查看背包确认。"
    if result.get("targetTip"):
        return result["targetTip"]
    return "操作已执行；如果没有成功，请先查看房间确认目标位置。"


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/scenarios")
def get_scenarios():
    return jsonify(public_scenarios())


@app.get("/api/engine")
def engine_status():
    return jsonify({
        "available": textworld is not None,
        "engine": "textworld-json",
        "textworldVersion": getattr(textworld, "__version__", None) if textworld else None,
        "twMake": find_tw_make(),
        "zMachine": "当前使用原生 .json 环境；如需传统 Z-machine 文件，需要额外配置 Inform。",
        "error": str(TEXTWORLD_IMPORT_ERROR) if TEXTWORLD_IMPORT_ERROR else None,
    })


@app.post("/api/generate")
def generate_game():
    data = request.get_json(silent=True) or {}
    scenario_id = data.get("scenario")
    difficulty = data.get("difficulty")
    if scenario_id not in GAME_SCENARIOS:
        return jsonify({"error": "无效场景，请选择 cooking、fire_safety 或 garbage_sorting"}), 400
    if difficulty not in GAME_SCENARIOS[scenario_id]["difficulties"]:
        return jsonify({"error": "无效难度，请选择 easy、medium 或 hard"}), 400
    try:
        game_id = str(uuid.uuid4())
        requested_seed = data.get("seed")
        seed = int(requested_seed) if requested_seed is not None else None
        session = create_session(scenario_id, difficulty, game_id, seed)
        game_sessions[game_id] = session
    except Exception as exc:
        return jsonify({"error": "真实 TextWorld 引擎不可用，未启用模拟 fallback", "detail": str(exc)}), 500
    return jsonify({
        "game_id": game_id,
        "scenario": scenario_id,
        "difficulty": difficulty,
        "config": GAME_SCENARIOS[scenario_id]["difficulties"][difficulty],
        "engine": session["engine"],
        "game_file": session["game_file"],
        "seed": session["seed"],
        "initialRoom": get_room(session, session["currentRoom"]),
        "initial_obs": describe_room(session, getattr(session["tw_state"], "feedback", "")),
        "objectiveSummary": target_summary(session),
        "targets": target_summary(session),
        "map": build_map(session),
        "admissibleCommands": visible_command_suggestions(session),
    })


@app.get("/api/game/<game_id>")
def get_game(game_id):
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "游戏不存在或已过期"}), 404
    return jsonify(response_payload(session, describe_room(session), teaching_tip="继续探索并完成所有目标。"))


@app.get("/api/game/<game_id>/map")
def get_game_map(game_id):
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "游戏不存在或已过期", "rooms": [], "connections": []}), 404
    return jsonify(build_map(session))


@app.post("/api/game/<game_id>/command")
def game_command(game_id):
    session = game_sessions.get(game_id)
    if not session:
        return jsonify({"error": "游戏不存在或已过期"}), 404
    command = (request.get_json(silent=True) or {}).get("command", "")
    if not command.strip():
        return jsonify({"error": "缺少 command 参数"}), 400
    if normalize(command) in {"help", "帮助"}:
        help_text = command_help(session)
        return jsonify(response_payload(session, describe_room(session), {"ok": True, "action": "帮助"}, "优先使用页面给出的中文建议指令。", help_text))
    tw_command, action = translate_command(session, command)
    if action in SCENE_STEP_ACTIONS:
        result = handle_target_step(session, tw_command)
        feedback_message = result.pop("feedback", "")
        response = describe_room(session, feedback_message)
        return jsonify(response_payload(session, response, result, result.pop("teachingTip", step_tip(session)), feedback_message))
    commands = command_sequence_for(session, tw_command, action)
    target = find_target_in_text(session, command) or find_target_in_text(session, tw_command)
    previous_score = int(getattr(session["tw_state"], "score", 0) or 0)
    previous_commands = set(getattr(session["tw_state"], "admissible_commands", []) or [])
    score = previous_score
    done = False
    feedback = ""
    try:
        for engine_command in commands:
            tw_state, score, done = session["env"].step(engine_command)
            session["tw_state"] = tw_state
            feedback = getattr(tw_state, "feedback", "") or ""
            if feedback.strip() == "Invalid command.":
                break
    except Exception as exc:
        return jsonify({"error": "真实引擎命令执行失败", "detail": str(exc)}), 500
    result = apply_command_side_effects(session, action, tw_command, previous_commands, previous_score, int(score or 0), bool(done))
    if target:
        result["targetName"] = target["name"]
        result["targetTip"] = target.get("tip", "")
    if len(commands) > 1:
        result["steps"] = len(commands)
    if feedback.strip() == "Invalid command.":
        session["mistakes"] += 1
        result["ok"] = False
    response = describe_room(session, feedback)
    log_message = command_log_message(session, action, result, feedback)
    return jsonify(response_payload(session, response, result, teaching_tip(session, action, result), log_message))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
