# -*- coding: utf-8 -*-
"""下载 CC-CEDICT 词典（CC-BY-SA）到 data/cedict/cedict.txt。

用法： python scripts/download_cedict.py
"""
import gzip
import urllib.request
from pathlib import Path

URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
OUT = Path(__file__).resolve().parents[1] / "data/cedict/cedict.txt"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("下载 CC-CEDICT ...")
    with urllib.request.urlopen(URL) as r:
        data = gzip.decompress(r.read())
    OUT.write_bytes(data)
    print("已保存:", OUT, "(", len(data) // 1024, "KB )")


if __name__ == "__main__":
    main()
