# -*- coding: utf-8 -*-
"""生成语法点注册表 data/grammar_points.json。

来源：官方《国际中文教育中文水平等级标准》语法点（GF0025-2021，数字化文本来自
krmanik/HSK-3.0，由 scripts/download_grammar.py 下载到 data/hsk_grammar/）。

每个条目：{id, level, cat, sub, label, label_full, pattern, exclude, examples}
- id: 官方编号（一01 -> "1-01"）
- pattern/exclude: 自动检测正则（人工维护，见 PATTERNS；结构性语法点无法用
  正则可靠检测则为 null，仅存在于注册表供作者标注/文档用）
- 检测正确性由 scripts/test_grammar_rules.py 回归保护

用法： python scripts/gen_grammar_registry.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/hsk_grammar"
OUT = ROOT / "data/grammar_points.json"

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}

# —— 人工维护的检测规则（id -> [pattern, exclude]）——
# 原 59 条 slug 规则映射到官方编号；结构性条目（句子成分/句型等）不配 pattern。
PATTERNS = {
    # ===== 一级 =====
    "1-02": [r"会|能(?!够)", None],                      # 能愿动词：会、能
    "1-03": [r"想(?!法)|要", r"要求|重要|只要|不要|快要|就要"],  # 能愿动词：想、要
    "1-04": [r"什么|谁|哪|几|多少|怎么", None],          # 疑问代词
    "1-06": [r"这|那|别的|有的", None],                  # 指示代词
    "1-08": [r"[一二两三四五六七八九十几百](个|本|杯|口|块|间|页|家)", None],  # 名量词
    "1-09": [r"非常|很|太|真(?!正)|最", None],           # 程度副词
    "1-10": [r"都|一块儿|一起", None],                   # 范围/协同副词
    "1-11": [r"马上|有时(?!候)", None],                  # 时间副词
    "1-12": [r"常常|再(?!见)", None],                    # 频率/重复副词
    "1-13": [r"也|还(?!是)", None],                      # 关联副词：还、也
    "1-14": [r"不(?!过|但|错)|没|别(?!的|人)", None],    # 否定副词 + 别
    "1-15": [r"从", None],                               # 从
    "1-16": [r"在", None],                               # 在
    "1-17": [r"跟|和", None],                            # 跟、和
    "1-18": [r"比(?!如|较)", None],                      # 比
    "1-19": [r"还是", None],                             # 连接：还是
    "1-20": [r"的(?!话)", None],                         # 结构助词：的
    "1-21": [r"了", None],                               # 动态助词：了
    "1-22": [r"吧", None],                               # 语气助词：吧
    "1-42": [r"正在", None],                             # 进行态
    "1-45": [r"吗？", None],                             # 用"吗"提问
    "1-48": [r"是不是|好不好|行不行|有没有", None],      # 正反疑问
    # ===== 二级 =====
    "2-02": [r"应该|该", None],                          # 能愿动词：该、应该
    "2-03": [r"愿意", None],                             # 能愿动词：愿意
    "2-05": [r"多久|为什么|怎么样|怎样", None],          # 疑问代词（二级）
    "2-06": [r"别人|大家|它|咱|自己", None],             # 人称代词（二级）
    "2-07": [r"那么|那样|这么|这样", None],              # 指示代词（二级）
    "2-09": [r"千(?!克)|万|亿", None],                   # 千、万、亿
    "2-10": [r"[一二两三四五六七八九十几百](层|封|件|条|位)", None],  # 名量词（二级）
    "2-11": [r"[一二两三四五六七八九十几](遍|次|场|回)", None],       # 动量词
    "2-12": [r"[一二两三四五六七八九十几半个](分钟|年|天|周)", None], # 时量词
    "2-13": [r"多么|更|十分|特别|挺|有点儿|有一点儿", None],  # 程度副词（二级）
    "2-14": [r"全(?!国|家|年|身|体|部)|一共|只(?!要|能)", None],  # 范围副词
    "2-15": [r"刚|忽然|一直|已经", None],                # 时间副词（二级）
    "2-16": [r"重新|经常|老是|又", None],                # 频率副词（二级）
    "2-17": [r"就(?!要|是)", None],                      # 关联副词：就
    "2-18": [r"故意", None],                             # 方式副词
    "2-19": [r"必须|差不多|好像|一定|也许", None],       # 情态副词
    "2-20": [r"才|正好", None],                          # 语气副词
    "2-21": [r"当(?!时|然)", None],                      # 当
    "2-22": [r"往", None],                               # 往
    "2-23": [r"(?<!方)向", None],                        # 向
    "2-25": [r"对[一-鿿]", r"对不起|对面|对话|不对", ],  # 对 介词
    "2-26": [r"给", None],                               # 给
    "2-27": [r"离(?!开)", None],                         # 离
    "2-28": [r"(?<!因)为(?!什么)", None],                # 为
    "2-29": [r"或者|或(?=[一-鿿])", None],               # 或、或者
    "2-31": [r"(?<!记)(?<!觉)(?<!懂)(?<!取)得(?!到|出)", None],  # 结构助词：得
    "2-32": [r"[看说听去吃见学来读到住过]过(?!年|去|来|马路)", None],  # 动态助词：过
    "2-33": [r"着", None],                               # 动态助词：着
    "2-34": [r"啊", None],                               # 语气助词：啊
    "2-36": [r"喂", None],                               # 喂
    "2-42": [r"不一会儿", None],                         # 不一会儿
    "2-44": [r"越来越|越[一-鿿]+越", None],              # 越来越 / 越…越
    "2-46": [r"又[一-鿿]{1,4}又", None],                 # 又…又…
    "2-47": [r"以前|以后", None],                        # …以前/以后
    "2-49": [r"[听看说写做学吃洗弄](错|懂|完|好|清楚|干净)", None],  # 结果补语1
    "2-50": [r"(出|回|过|进|起|上|下)(来|去)", None],    # 趋向补语1
    "2-62": [r"然后|接着", None],                        # 承接复句
    "2-63": [r"不但|而且", None],                        # 递进复句
    "2-65": [r"虽然|但是|可是|不过|(?<!不)但", None],    # 转折复句
    "2-66": [r"如果|的话，", None],                      # 假设复句
    "2-67": [r"只要", None],                             # 条件复句：只要…就
    "2-68": [r"因为|所以", None],                        # 因果复句
    "2-75": [r"(好吗|可以吗|行吗|怎么样)？", None],      # 用"好吗/怎么样"提问
    "2-77": [r"呢？", None],                             # 用"呢"省略式提问
    "2-80": [r"该[一-鿿]{1,6}了", None],                 # 该…了
    "2-81": [r"(就要|快要)[一-鿿]{0,6}了", None],        # 要/快要/就要…了
}

# 官方未单列、但对学习者有用的自定义条目
CUSTOM = [
    {"id": "x-erhua", "level": 1, "cat": "其他", "sub": "语音",
     "label": "儿化", "label_full": "儿化（哪儿/玩儿/一会儿…）",
     "pattern": r"哪儿|这儿|那儿|玩儿|一会儿|一下儿|条儿|孩儿|事儿|点儿|空儿|活儿|话儿",
     "exclude": None, "examples": ["你的家在哪儿？", "我们出去玩儿吧。"]},
    {"id": "x-yibian", "level": 2, "cat": "其他", "sub": "格式",
     "label": "一边…一边", "label_full": "一边…一边…（动作同时进行）",
     "pattern": r"一边[^。！？]{1,12}一边", "exclude": None,
     "examples": ["他一边听音乐，一边干活儿。"]},
]


def short_label(text):
    """官方条目名 -> 短标签：取"："前的名称，若有列举则附前几项。"""
    text = text.strip()
    if "：" in text:
        name, items = text.split("：", 1)
        items = items.replace("、", "/").replace("；", "/")
        if len(items) > 10:
            items = items[:9] + "…"
        return f"{name.strip()}({items})"
    return text if len(text) <= 14 else text[:13] + "…"


def parse_level(path, level):
    entries = []
    cat = sub = ""
    cur = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        mh = re.match(r"^A\.\d+\.\d+(\.\d+)?\s+(.+)$", line)
        mp = re.match(r"^【(一|二|三|四|五|六)(\d+)】\s*(.+)$", line)
        if mh:
            if mh.group(1):
                sub = mh.group(2).strip()
            else:
                cat = mh.group(2).strip()
                sub = ""
            cur = None
            continue
        if mp:
            pid = f"{CN_NUM[mp.group(1)]}-{mp.group(2)}"
            pat, exc = PATTERNS.get(pid, (None, None))
            cur = {"id": pid, "level": level, "cat": cat, "sub": sub,
                   "label": short_label(mp.group(3)), "label_full": mp.group(3).strip(),
                   "pattern": pat, "exclude": exc, "examples": []}
            entries.append(cur)
            continue
        if cur is not None and line and not line.startswith("A."):
            # 例句行（只收句子样式的，最多2条）
            if len(cur["examples"]) < 2 and re.search(r"[。？！]$", line):
                cur["examples"].append(line)
    return entries


def main():
    entries = []
    for lvl, fname in [(1, "hsk_1.txt"), (2, "hsk_2.txt"), (3, "hsk_3.txt"), (4, "hsk_4.txt"), (5, "hsk_5.txt")]:
        entries.extend(parse_level(SRC / fname, lvl))
    entries.extend(CUSTOM)
    # 去重：高级别原文会重列低级条目（升级用法），保留首次出现（低级别定义）
    seen, uniq = set(), []
    for e in entries:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)
    entries = uniq
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    withp = sum(1 for e in entries if e["pattern"])
    print(f"注册表: {len(entries)} 条（含检测规则 {withp} 条）-> {OUT.name}")
    unknown = set(PATTERNS) - {e["id"] for e in entries}
    if unknown:
        print("⚠️ PATTERNS 中有未匹配到官方条目的 id:", unknown)


if __name__ == "__main__":
    main()
