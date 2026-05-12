#!/usr/bin/env python3
"""简单接口冒烟测试。

先运行：python app.py
再运行：python test_api.py
"""

import json

import requests


BASE_URL = "http://127.0.0.1:5003"
HEADERS = {"Content-Type": "application/json"}


def post(path, payload):
    response = requests.post(f"{BASE_URL}{path}", headers=HEADERS, data=json.dumps(payload), timeout=10)
    print(path, response.status_code)
    print(response.json())
    return response


def main():
    response = post("/api/generate", {"scenario": "cooking", "difficulty": "easy"})
    if response.status_code != 200:
        return

    game_id = response.json()["game_id"]
    for command in ["look", "take 番茄", "go east", "take 鸡蛋", "go west", "take 食用油", "cook 番茄炒蛋"]:
        post(f"/api/game/{game_id}/command", {"command": command})


if __name__ == "__main__":
    main()
