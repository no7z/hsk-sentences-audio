# -*- coding: utf-8 -*-
"""审核标红：把可疑 token（常见多音字 / 未收录词）挑出来供人工秒批。"""

# 常见上下文多音字（保守列表，宁可多标；命中≠一定错，人工确认后沉淀进 overrides）
POLYPHONE = set("的地得了着行长重还差觉好数教乐曲血都为便分种当空要东西识没干发少中")


def review_flags(sid, tokens, vocab):
    """tokens: [{word, pinyin, ...}]，返回该句的标红条目列表。"""
    out = []
    for t in tokens:
        w = t["word"]
        reasons = []
        if any(c in POLYPHONE for c in w):
            reasons.append("polyphone?")
        if w not in vocab and len(w) > 1:
            reasons.append("OOV")
        if reasons:
            out.append(f"{sid} 「{w}」{t['pinyin']} -> {','.join(reasons)}")
    return out
