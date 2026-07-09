# -*- coding: utf-8 -*-
"""分词：jieba 为主 + 例外表拆分。

jieba 对自然词边界远好于 CC-CEDICT 最大匹配（后者会把 去火车站→去火|车站、
吃鸡蛋→吃鸡|蛋 这类切坏）。jieba 偶尔过度合并（今天天气、我想学），用 seg_exceptions
显式拆开即可，维护成本远低于给最大匹配维护黑名单。
"""
import jieba

_PUNCT = '，。、！？；：""''（）《》…—'


def segment(text, vocab=None, seg_exceptions=None, blocklist=None):
    """jieba 分词 + 例外表拆分。vocab/blocklist 保留以兼容旧签名（未使用）。"""
    seg_exceptions = seg_exceptions or {}
    out = []
    # HMM=False：关掉 jieba 的新词猜测，避免 班有/北都/有山 这类瞎合并
    for w in jieba.lcut(text, HMM=False):
        if w in _PUNCT or w.strip() == "":
            continue
        out.extend(seg_exceptions.get(w, [w]))
    return out
