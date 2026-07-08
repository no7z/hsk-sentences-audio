# -*- coding: utf-8 -*-
"""分词：基于 CC-CEDICT 的正向最大匹配（保证每个词都在词典里）+ 分词例外表。"""

_PUNCT = '，。、！？；：""''（）《》…—'


def maxmatch(text, vocab, maxlen=6):
    """正向最大匹配。标点跳过；单字兜底。"""
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] in _PUNCT:
            i += 1
            continue
        for L in range(min(maxlen, n - i), 0, -1):
            w = text[i:i + L]
            if w in vocab or L == 1:
                tokens.append(w)
                i += L
                break
    return tokens


def segment(text, vocab, seg_exceptions):
    """最大匹配 + 例外表拆分（如 买东西 -> 买|东西）。"""
    out = []
    for w in maxmatch(text, vocab):
        out.extend(seg_exceptions.get(w, [w]))
    return out
