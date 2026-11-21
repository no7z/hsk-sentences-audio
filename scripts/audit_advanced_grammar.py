# -*- coding: utf-8 -*-
"""HSK 7–9（GF0025-2021 高等）148 个语法点在 hsk7 记录中的覆盖审计。

只读：读取 data/hsk_grammar/hsk_7-9.txt（官方语法点数字化文本）和 dist/sentences.json，
输出 docs/advanced-grammar-coverage.json。不改 build、grammar_points.json 或任何记录。

检测规则（RULES）人工维护，两类：
- ("tok", {...})：句中某个 jieba token 恰好等于集合中的词（单字虚词用这个，避免 即使/立即 之类误报）
- ("re", pattern[, exclude])：对中文原句做正则
结构性语法点（宾语语义类型、把字句致使义、多重复句、句群等）没有可靠的自动规则，标为 manual。
匹配是“候选”，不是语法判定：报告给每个点列出例句 ID，供人工抽查。

用法： python scripts/audit_advanced_grammar.py [--examples N]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/hsk_grammar/hsk_7-9.txt"
OUT = ROOT / "docs/advanced-grammar-coverage.json"

ADJ1 = "高低大小重轻多少强弱优快慢早晚长短深浅难易好坏冷热"
RULES = {
    1: ("tok", {"需"}),
    2: ("tok", {"何", "何时", "何处", "何种", "何以", "何在"}),
    3: ("re", r"兹|另一|另(?=[有外])|(?<![应活])该(?=(公司|企业|项目|地区|产品|学校|小说|电影|药|案|书|片|城市|部门|国|校|市|县|厂|店))"),
    4: ("re", r"[一二两三四五六七八九十几百千万数](栋|粒|枚|则|盏)|人次"),
    5: ("re", r"极为"),
    6: ("re", r"尽(?=(前头|后头|北边|南边|东边|西边|里头|底下|头上))"),
    7: ("tok", {"蛮"}),
    8: ("re", r"颇"),
    9: ("re", r"稍稍"),
    10: ("re", r"尤为"),
    11: ("re", r"越发"),
    12: ("tok", {"凡", "凡是", "凡事"}),
    13: ("tok", {"皆"}),
    14: ("re", r"统统"),
    15: ("re", r"唯独"),
    16: ("tok", {"即"}),
    17: ("re", r"历来"),
    18: ("re", r"尚(未|无|需|不|有|待|在|可|且)"),
    19: ("re", r"向来"),
    20: ("re", r"频频"),
    21: ("re", r"再度"),
    22: ("tok", {"亦"}),
    23: ("re", r"(尚|从|至今|还|并|仍|均)未(?!来|免|必)|(?<![从尚])未(?=(到|曾|能|经|见|婚|满|完|有|被|做|去|听|变|动|定|成功))"),
    24: ("tok", {"勿", "请勿", "切勿", "勿念", "勿忘"}),
    25: ("re", r"不由得"),
    26: ("re", r"顺便"),
    27: ("re", r"一连"),
    28: ("re", r"按说"),
    29: ("re", r"必定"),
    30: ("re", r"不妨"),
    31: ("re", r"何必"),
    32: ("re", r"莫非"),
    33: ("re", r"白白"),
    34: ("re", r"反倒"),
    35: ("re", r"分明(?=(是|看|听|就|在|知道|已经|说|有|不|没|想))"),
    36: ("re", r"怪不得"),
    37: ("re", r"好在"),
    38: ("tok", {"乃", "乃是"}),
    39: ("re", r"难怪"),
    40: ("re", r"偏偏"),
    41: ("re", r"索性"),
    42: ("re", r"万万"),
    43: ("re", r"未免"),
    44: ("re", r"无非"),
    45: ("re", r"幸好"),
    46: ("re", r"幸亏"),
    47: ("re", r"终究"),
    48: ("re", r"顺着"),
    49: ("re", r"当着"),
    50: ("re", r"就[^，。！？]{1,18}(问题|事情|事件|情况|方案|计划|议题|这一点|此事)[^，。！？]{0,4}(进行|做|作|发表|展开|谈|讨论|交换|提出|达成|表态|说明)"),
    51: ("tok", {"趁", "趁着"}),
    52: ("re", r"基于"),
    53: ("re", r"依(?=(我|你|您|他|她|大家|你们|我们)(看|说|的|之见))"),
    54: ("tok", {"及"}),
    55: ("re", r"继而|要不是"),
    56: ("tok", {"之"}),
    57: ("re", r"而已"),
    58: ("tok", {"矣"}),
    59: None,
    60: ("re", r"爱(\S)不\1"),
    61: ("re", r"半[^半，。！？]半[^半，。！？]"),
    62: ("re", r"东[^东西，。！？]西[^东西，。！？]"),
    63: ("re", r"非[^非，。！？]非[^非，。！？常]"),
    64: ("re", r"忽[^忽，。！？]忽"),
    65: ("re", r"连[^连带，。！？]带[^带，。！？]"),
    66: ("re", rf"时[{ADJ1}有而断隐][，、]?时"),
    67: ("re", r"自([^自，。！？])自([^自，。！？])"),
    68: ("re", r"巴不得"),
    69: ("re", r"别提了"),
    70: ("re", r"除此之外"),
    71: ("re", r"归根到底|归根结底"),
    72: ("re", r"可不是"),
    73: ("re", r"没说的"),
    74: ("re", r"无论如何"),
    75: ("re", r"由此可见"),
    76: ("re", r"与此同时"),
    77: ("re", r"这样一来"),
    78: ("re", r"综上所述"),
    79: ("re", r"总的来说|总而言之"),
    80: ("re", r"不知[^，。！？]{0,8}才?好"),
    81: ("re", r"所谓[^。！？]*就是"),
    82: ("re", r"(无非|不过|只是)[^。！？]*(而已|罢了)"),
    83: ("re", r"以[^，。！？为]{1,10}为(?![了止])", r"以为|认为"),
    84: ("re", r"因[^，。！？为]{1,10}而"),
    85: None,
    86: ("re", r"得(不行|要命|要死)"),
    87: ("re", r"个(不停|没完|不住)"),
    88: None,
    89: ("re", r"被[^，。！？]{1,12}所(?!以|有|在|谓|得)|(?<!因)为[^，。！？]{1,8}所(?=(不|信|欢|喜|接|知|用|理|重|认|吸|感|打|迷|困|动|左|害|骗|拥|支|赞|采|称|爱|熟))"),
    90: ("re", rf"比起|[{ADJ1}]于(?!是)", r"[对属位等终至由处关基鉴善便过]于"),
    91: ("re", r"一面[^。！？]*一面"),
    92: ("re", r"此后"),
    93: ("re", r"起初[^。！？]*才"),
    94: ("re", r"别说[^。！？]*(连|即使)|(连|即使)[^。！？]*别说"),
    95: ("re", r"何况"),
    96: ("re", r"进而"),
    97: ("re", r"况且"),
    98: ("re", r"连[^。！？]*更不用说"),
    99: ("re", r"乃至"),
    100: ("tok", {"且"}),
    101: ("re", r"甚至于"),
    102: ("re", r"或(?!许|者)[^或，。！？]{1,10}，或(?!许|者)"),
    103: ("re", r"宁可|宁愿"),
    104: ("re", r"与其[^。！？]*不如"),
    105: ("re", r"与其[^。！？]*(宁可|宁愿)"),
    106: ("re", r"，而(?!且|已|是)|，[^。！？]*则"),
    107: ("re", r"，[^。！？]*(反倒|(?<![颠打摔推跌晕歪没不])倒(?![了下在闭霉车班是入出进退塌掉计数影映]))"),
    108: ("re", r"倘若|(^|，)若"),
    109: ("re", r"(倘若|假设|假使|(^|，)若)[^。！？]*(就|那么?)"),
    110: ("re", r"幸亏[^。！？]*(要不然|不然|要不|否则)"),
    111: ("re", r"别管[^。！？]*都"),
    112: ("re", r"(^|，)任(?![务何性意命职教])[^。！？]*也"),
    113: ("re", r"，故(?![事意乡障居宫人])"),
    114: ("re", r"鉴于"),
    115: ("re", r"以致"),
    116: ("re", r"以至于"),
    117: ("re", r"之所以[^。！？]*是(因为|由于)"),
    118: ("re", r"固然[^。！？]*也"),
    119: ("re", r"固然[^。！？]*(但|可是|不过)"),
    120: ("re", r"即便[^。！？]*也"),
    121: ("re", r"虽说[^。！？]*(但|可是|不过)"),
    122: ("re", r"纵然[^。！？]*也"),
    123: ("re", r"，以(?![免致至为便及后前来上下外内往])"),
    124: ("re", r"以免|免得"),
    125: ("re", r"也就是说"),
    126: ("re", r"([^\s，。！？])就\1个"),
    127: ("re", r"([^\s，。！？]{1,2})就\1[^。！？]*，别"),
    128: None,
    129: ("re", r"(何必|何苦)[^。！？]*呢"),
    130: ("re", r"话又说回来"),
    131: ("re", r"([^\s，。！？]{1,2})也?不是，不\1也不是"),
    132: ("re", r"(也好|也罢)[^。！？]*(也好|也罢)"),
    133: ("re", r"([^\s，。！？])了又([^\s，。！？])，\2了又\1"),
    134: ("re", r"([^\s，。！？])也\1不[^，。！？]*，[^，。！？]{0,6}?([^\s，。！？])也\2不"),
    135: ("re", r"别提有?多"),
    136: ("re", r"不知[^，。！？]{1,3}的"),
    137: ("re", r"(话说?|说)是这么说"),
    138: ("re", r"(看|瞧)你那[^，。！？]{0,3}样"),
    139: ("re", r"看在[^，。！？]+面子上"),
    140: ("re", r"哪有[^，。！？]+这么|有[^，。！？]+这样[^，。！？]*吗"),
    141: ("re", r"什么[^，。！？]{1,3}的[^，。！？]{1,3}的"),
    142: ("re", r"(说|想)到哪儿去了"),
    143: ("re", r"无所谓([^\s，。！？]{1,2})不\1"),
    144: ("re", r"要([^\s，。！？]{1,2})[有没]\1"),
    145: None, 146: None, 147: None, 148: None,
}
MANUAL_REASON = {
    59: "数量词+抽象事物（一身本领、一团和气）：结构性，需人工标注",
    85: "宾语语义类型（方式/工具/材料/目的宾语）：需句法语义判断",
    88: "把字句表致使（把丈夫死了）：需语义判断",
    128: "三重及以上多重复句：需句法分析",
    145: "句群（带关联词语）：本数据为单句，按设计不适用",
    146: "句群（不带关联词语）：本数据为单句，按设计不适用",
    147: "联合关系句群：本数据为单句，按设计不适用",
    148: "偏正关系句群：本数据为单句，按设计不适用",
}

# 没有自动规则、经人工逐句判定的例句（2026-11-21）。这些点的状态记为 covered，method 为 manual。
MANUAL_EXAMPLES = {
    59: ["hsk7-2420", "hsk7-0561", "hsk7-3197", "hsk7-4439", "hsk7-3333", "hsk7-4333"],  # 一片苦心、一片痴心、一腔热血、一肚子的怒气、一股…热潮、一股旅游热
    85: ["hsk7-2819", "hsk7-5570", "hsk7-5571", "hsk7-5572", "hsk7-5573"],  # 浇水（材料）、存个活期/寄航空（方式）、吃大碗（工具）、跑订单（目的）
    88: ["hsk7-5574", "hsk7-5575"],  # 把犯人跑了、把老伴病了
    128: ["hsk7-0371", "hsk7-5452", "hsk7-5576", "hsk7-5577"],
}


def parse_points():
    pts = {}
    for line in SRC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*【七\s*[—–\-ー]\s*九\s*([0-9OＯ]{3})\s*】\s*(.+)", line)
        if m:
            n = int(m.group(1).replace("O", "0").replace("Ｏ", "0"))
            pts[n] = m.group(2).strip()
    return pts


def render_md(out):
    pts, s = out["points"], out["summary"]
    cov = [p for p in pts if p["status"] == "covered"]
    one = sum(p["count"] == 1 for p in cov)
    lines = [
        "# HSK 7–9 语法点覆盖审计（GF0025-2021 高等，148 点）", "",
        f"- 审计对象：dist/sentences.json 中 {out['records_checked']} 条 hsk7 记录；规则见 `scripts/audit_advanced_grammar.py`，明细见 `docs/advanced-grammar-coverage.json`。",
        "- 方法：单字虚词按 jieba token 匹配，固定格式按正则匹配；每条规则都在官方例句上自测通过，高风险规则经抽查收紧。匹配是候选，不等于语法判定。059/085/088/128 没有自动规则，例句为人工逐句判定（见 `MANUAL_EXAMPLES`）。",
        f"- 结果：**已覆盖 {s['covered']}**、**未覆盖 {s['missing']}**、**无法自动判定 {s['manual']}**（共 148）；已覆盖点中 {one} 个只有 1 句例句。", "",
    ]
    if s["missing"]:
        lines += ["## 未覆盖", "", "| 编号 | 语法点 |", "|---|---|"]
        lines += [f"| {p['id']} | {p['label']} |" for p in pts if p["status"] == "missing"]
        lines.append("")
    lines += ["## 无法自动判定", "", "| 编号 | 语法点 | 说明 |", "|---|---|---|"]
    lines += [f"| {p['id']} | {p['label']} | {p['manual_reason']} |" for p in pts if p["status"] == "manual"]
    lines += ["", "## 已覆盖（例句数）", "", "| 编号 | 语法点 | 例句数 | 例 |", "|---|---|---|---|"]
    lines += [f"| {p['id']} | {p['label'][:24]}{'（人工判定）' if p.get('method') == 'manual' else ''} | {p['count']} | {p['examples'][0]['id']} {p['examples'][0]['chinese']} |" for p in cov]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", type=int, default=3)
    args = ap.parse_args()
    pts = parse_points()
    assert sorted(pts) == list(range(1, 149)), "expected 148 points"
    recs = [r for r in json.loads((ROOT / "dist/sentences.json").read_text(encoding="utf-8")) if r["hsk_level"] == 7]
    compiled = {}
    for n, rule in RULES.items():
        if rule and rule[0] == "re":
            compiled[n] = (re.compile(rule[1]), re.compile(rule[2]) if len(rule) > 2 and rule[2] else None)
    hits = {n: [] for n in pts}
    for r in recs:
        zh, toks = r["chinese"], {t["word"] for t in r["tokens"]}
        for n, rule in RULES.items():
            if not rule:
                continue
            if rule[0] == "tok":
                ok = bool(toks & rule[1])
            else:
                pat, exc = compiled[n]
                ok = bool(pat.search(zh)) and not (exc and exc.search(zh) and not pat.search(exc.sub("", zh)))
            if ok:
                hits[n].append(r["id"])
    by_id = {r["id"]: r["chinese"] for r in recs}
    for n, ids in MANUAL_EXAMPLES.items():
        assert RULES[n] is None and all(i in by_id for i in ids), n
        hits[n] = list(ids)
    points = []
    for n in range(1, 149):
        if n in MANUAL_EXAMPLES:
            status = "covered"
        else:
            status = "manual" if RULES[n] is None else ("covered" if hits[n] else "missing")
        points.append({
            "id": f"7-9-{n:03d}", "label": pts[n], "status": status, "count": len(hits[n]),
            **({"method": "manual"} if n in MANUAL_EXAMPLES else {}),
            "examples": [{"id": i, "chinese": by_id[i]} for i in hits[n][:args.examples]],
            **({"manual_reason": MANUAL_REASON[n]} if status == "manual" else {}),
        })
    summary = {s: sum(p["status"] == s for p in points) for s in ("covered", "missing", "manual")}
    out = {
        "standard": "GF0025-2021", "band": "7-9", "points_total": 148, "records_checked": len(recs),
        "method": "rule-based candidate matching (token sets for single-character function words, regex for fixed formats); matches are candidates for manual spot-check, not grammatical verification",
        "summary": summary, "points": points,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    OUT.with_suffix(".md").write_text(render_md(out), encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False))
    for p in points:
        if p["status"] == "missing":
            print("MISSING", p["id"], p["label"])


if __name__ == "__main__":
    main()
