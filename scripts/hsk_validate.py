# -*- coding: utf-8 -*-
"""HSK 校验器：检查句子集对某一目标 HSK 等级的 containment（超纲）与 coverage（覆盖）。

分词独立于主管线：直接用 HSK 词表做最大匹配（避免 CC-CEDICT 生僻词造成的假分词），
再给每个词标注它所属的最低 HSK 级别。

用法： python scripts/hsk_validate.py --level 1 [--standard new]
"""
import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WL = ROOT / "data/hsk_wordlist"
PUNCT = set("，。、！？；：""''（）《》…—")


def load_levels(standard="new", maxlvl=6):
    """返回 word -> 最低 HSK 级别 的映射，及 每级词集合。"""
    word_level, per_level = {}, {}
    for lvl in range(1, maxlvl + 1):
        f = WL / f"{standard}_{lvl}.json"
        if not f.exists():
            continue
        ws = {e["simplified"] for e in json.loads(f.read_text(encoding="utf-8"))
              if e.get("simplified")}
        per_level[lvl] = ws
        for w in ws:
            word_level.setdefault(w, lvl)   # 首次出现即最低级
    return word_level, per_level


def hsk_segment(text, word_level, target, maxlen=6):
    """分词，选择使“超过目标级的词最少”的切法（同代价下偏好更长的词）。

    这样像 个人=个+人、做饭=做+饭、有没有=有+没+有 这类可由低级词组成的串，
    不会被误判为高级词；只有真正无法用≤target 词拆出的串才算超纲。
    """
    n = len(text)
    INF = float("inf")
    # best[i] = (超纲词数, 词数, 切分列表) 从位置 i 到末尾的最优
    best = [None] * (n + 1)
    best[n] = (0, 0, [])
    for i in range(n - 1, -1, -1):
        if text[i] in PUNCT:
            best[i] = best[i + 1]
            continue
        cand = None
        for L in range(1, min(maxlen, n - i) + 1):
            w = text[i:i + L]
            if not (w in word_level or L == 1):
                continue
            sub = best[i + L]
            if sub is None:
                continue
            lvl = word_level.get(w)
            over = (1 if (lvl is not None and lvl > target) else 0)
            oov = (1 if lvl is None else 0)   # 不在词表：单字兜底，计为轻微代价
            key = (sub[0] + over, sub[1] + 1 + oov * 0, [w] + sub[2])
            # 主排序：超纲词数最少；次：词数最少（偏好长词）
            if cand is None or (key[0], key[1]) < (cand[0], cand[1]):
                cand = key
        best[i] = cand if cand else (0, 0, [text[i]])
    return best[0][2] if best[0] else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--standard", default="new")
    args = ap.parse_args()

    word_level, per_level = load_levels(args.standard)
    vocab = set(word_level)
    target = args.level
    target_words = per_level.get(target, set())

    src = yaml.safe_load((ROOT / f"data/sentences/hsk{target}.yaml").read_text(encoding="utf-8"))
    sentences = [s["chinese"] for s in src["sentences"]]

    used_target = set()
    over_level = {}   # word -> level (>target)
    oov = set()       # 不在任何 HSK 词表（专名等）
    sent_issues = []

    for zh in sentences:
        bad = []
        for w in hsk_segment(zh, word_level, target):
            lvl = word_level.get(w)
            if lvl is None:
                if not (len(w) == 1 and w in "".join(vocab)):  # 单字可能是更长词的一部分
                    oov.add(w)
                    bad.append(f"{w}(?)")
            elif lvl > target:
                over_level[w] = lvl
                bad.append(f"{w}(HSK{lvl})")
            elif lvl <= target:
                used_target.add(w)
        if bad:
            sent_issues.append((zh, bad))

    cov = len(used_target)
    total = len(target_words)
    print(f"===== HSK {args.standard} 一级校验（目标 HSK{target}，{total} 词）=====\n")
    print(f"【Coverage 覆盖】{cov}/{total} = {cov*100//total}%")
    missing = sorted(target_words - used_target)
    print(f"  未覆盖 {len(missing)} 词： {' '.join(missing)}\n")

    print(f"【Containment 超纲】{len(sent_issues)} 句含非本级词：")
    for zh, bad in sent_issues:
        print(f"  {zh}  ->  {' '.join(bad)}")
    print(f"\n  超纲词（>HSK{target}）: {len(over_level)}")
    for w, l in sorted(over_level.items(), key=lambda x: x[1]):
        print(f"    {w} = HSK{l}")
    if oov:
        print(f"  不在 HSK 词表（专名/其他）: {' '.join(sorted(oov))}")


if __name__ == "__main__":
    main()
