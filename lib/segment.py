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


def segment(text, vocab, seg_exceptions, blocklist=None):
    """基于 CC-CEDICT 的最大匹配分词。

    - blocklist：从匹配词表剔除会导致坏切分的“伪词”（如 说中/想睡/买东西），
      让最大匹配自然切对（说|中文、想|睡觉、买|东西）。
    - seg_exceptions：兜底的显式拆分（token -> [子词…]）。
    """
    if blocklist:
        vocab = vocab - set(blocklist)
    out = []
    for w in maxmatch(text, vocab):
        out.extend(seg_exceptions.get(w, [w]))
    return out
