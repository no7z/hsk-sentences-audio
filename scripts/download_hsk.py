# -*- coding: utf-8 -*-
"""下载 HSK 3.0（新标准）分级词表到 data/hsk_wordlist/。

数据来源：https://github.com/drkameleon/complete-hsk-vocabulary
（社区对官方《国际中文教育中文水平等级标准》GF0025-2021 的数字化，与官方口径约有 ~1% 出入）

用法： python scripts/download_hsk.py
"""
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/main/wordlists/exclusive/new"
OUT = Path(__file__).resolve().parents[1] / "data/hsk_wordlist"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for lvl in range(1, 8):   # 1-6 级 + 7（7-9 高等合并）
        url = f"{BASE}/{lvl}.json"
        try:
            with urllib.request.urlopen(url) as r:
                data = r.read()
            (OUT / f"new_{lvl}.json").write_bytes(data)
            print(f"level {lvl}: {len(data)//1024} KB")
        except Exception as e:
            print(f"level {lvl}: 跳过 ({e})")


if __name__ == "__main__":
    main()
