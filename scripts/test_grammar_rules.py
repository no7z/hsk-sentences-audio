# -*- coding: utf-8 -*-
"""语法点检测规则回归测试。

每次修改 gen_grammar_registry.py 的 PATTERNS 后运行：
  python scripts/gen_grammar_registry.py && python scripts/test_grammar_rules.py

历史误报（想法/你的话/不但/记得…）都固化为负例，防止规则改动回归。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build import detect_grammar  # noqa: E402

# (句子, 必须命中的id, 必须不命中的id)
CASES = [
    # —— 历史误报，永久负例 ——
    ("他改变了想法。",              [],            ["1-03"]),       # 想法 ≠ 能愿"想"
    ("我记得你，也记住了你的话。",   ["1-13"],      ["2-66", "2-31"]),  # 你的话≠如果…的话; 记得≠得补语
    ("他不但会英语，而且说得很流利。", ["2-63", "2-31", "1-02"], ["2-65"]),  # 不但≠转折"但"
    ("别的东西我不要。",            [],            []),             # 别的≠禁止"别"
    ("你为什么不早说？",            ["2-05"],      ["2-28"]),       # 为什么≠介词"为"
    ("我们走的方向不对。",          [],            ["2-23"]),       # 方向≠介词"向"
    ("他离开家去外地了。",          [],            ["2-27"]),       # 离开≠介词"离"
    ("当时我还是小学生。",          ["1-19"],      ["2-21"]),       # 当时≠介词"当"
    ("他是真正的好人。",            [],            ["1-09"]),       # 真正≠程度副词"真"
    # —— 正例 ——
    ("如果你有时间的话，来我家玩儿吧。", ["2-66", "1-22", "x-erhua"], []),
    ("你的家在哪儿？",              ["1-04", "x-erhua", "1-16"], []),
    ("他走得很快。",                ["2-31", "1-09"], []),
    ("我看过这个电影。",            ["2-32"],      []),
    ("他过来了。",                  ["2-50"],      ["2-32"]),       # 过来=趋向补语,非经历态
    ("天气越来越冷。",              ["2-44"],      []),
    ("火车快要到了。",              ["2-81"],      []),
    ("大家为我们加油。",            ["2-28"],      []),
    ("请举手回答问题。",            ["1-34"],      []),
    ("你会说中文吗？",              ["1-45", "1-02"], []),
    ("他是不是学生？",              ["1-48"],      []),
    ("我是中国人，你呢？",          ["2-77"],      []),
    ("他一边听音乐，一边干活儿。",   ["x-yibian"],  []),
    ("她的头发又黑又长。",          ["2-46"],      []),
]


def main():
    failed = 0
    for zh, must, must_not in CASES:
        got = set(detect_grammar(zh))
        for m in must:
            if m not in got:
                print(f"✗ [{zh}] 应命中 {m}，实际 {sorted(got)}")
                failed += 1
        for m in must_not:
            if m in got:
                print(f"✗ [{zh}] 不应命中 {m}，实际 {sorted(got)}")
                failed += 1
    total = sum(len(m) + len(n) for _, m, n in CASES)
    print(f"\n{'FAIL' if failed else 'PASS'}: {total - failed}/{total} 断言通过")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
