# -*- coding: utf-8 -*-
"""分词：jieba 为主 + 例外表拆分。

jieba 对自然词边界远好于 CC-CEDICT 最大匹配（后者会把 去火车站→去火|车站、
吃鸡蛋→吃鸡|蛋 这类切坏）。jieba 偶尔过度合并（今天天气、我想学），用 seg_exceptions
显式拆开即可，维护成本远低于给最大匹配维护黑名单。
"""
import jieba

_PUNCT = '，。、！？；：""''（）《》…—'


def _try_split(w, vocab, maxlen=6):
    """把不在词表的 token 尝试拆成全部在词表内的词序列（最长优先）。

    拆不干净（有任何一段不在词表，如 早点儿 的 儿）则返回 None，保留原 token。
    """
    parts, i, n = [], 0, len(w)
    while i < n:
        for L in range(min(maxlen, n - i), 0, -1):
            seg = w[i:i + L]
            if seg in vocab:
                parts.append(seg)
                i += L
                break
        else:
            return None
    return parts if len(parts) > 1 else None


def segment(text, vocab=None, seg_exceptions=None, blocklist=None):
    """jieba 分词 + 例外表 + 词表回拆。

    - HMM=False：关掉 jieba 的新词猜测，避免 班有/北都 这类瞎合并；
    - vocab（HSK 全级词表）：jieba 粘连出的非词表 token（坐地铁/很漂亮/给我发），
      若能完全拆成词表内的词则自动回拆——无需人工维护例外清单。
    """
    seg_exceptions = seg_exceptions or {}
    out = []
    for w in jieba.lcut(text, HMM=False):
        if w in _PUNCT or w.strip() == "":
            continue
        for t in seg_exceptions.get(w, [w]):
            if vocab and len(t) >= 2 and t not in vocab:
                sp = _try_split(t, vocab)
                out.extend(sp if sp else [t])
            else:
                out.append(t)
    return out
