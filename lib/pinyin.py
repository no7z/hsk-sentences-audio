# -*- coding: utf-8 -*-
"""拼音生成。

策略（原型踩坑后的定论）：
- pypinyin 提供句级上下文（多音字如 要/长/行 蒙对），但默认丢轻声（认识→shí）。
- CC-CEDICT 提供逐词标准拼音（含轻声5/儿化），但取首义项会错上下文多音字（要→yāo）。
两者错误互补，故：用 CC-CEDICT 的轻声/儿化词批量“播种”进 pypinyin 的 load_phrases_dict，
再叠加人工 overrides（真·上下文多音字）。句级算拼音→按字对齐到词→儿化音节合并。

注意：此拼音用于 JSON 文本字段。音频由 CosyVoice 自带 G2P 合成（另一套），二者对多音字
基本一致；分歧交给审核标红 + 听测。
"""
import re
from pypinyin import lazy_pinyin, Style, load_phrases_dict

_TONE = {'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì',
         'o': 'ōóǒò', 'u': 'ūúǔù', 'ü': 'ǖǘǚǜ'}
_SYL = re.compile(r'^([a-zü:]+)([1-5])?$')
_HAN = re.compile(r'[一-鿿]')


def _syl_to_diacritic(syl):
    """数字调号音节 -> 声调符音节，如 ren4 -> rèn, shi5 -> shi, r5 -> r。"""
    m = _SYL.match(syl.lower())
    if not m:
        return syl
    base, tone = m.group(1), m.group(2)
    base = base.replace('u:', 'ü').replace('v', 'ü')
    if not tone or tone == '5':
        return base
    if 'a' in base:
        i = base.index('a')
    elif 'e' in base:
        i = base.index('e')
    elif 'ou' in base:
        i = base.index('o')
    else:
        vs = [k for k, c in enumerate(base) if c in 'aeiouü']
        if not vs:
            return base
        i = vs[-1]
    return base[:i] + _TONE[base[i]][int(tone) - 1] + base[i + 1:]


def cedict_word_toned(numbered):
    """CC-CEDICT 数字拼音串 -> 声调符音节 list（逐音节，不合并儿化）。

    儿化的合并留到输出阶段（token_pinyin / sentence_pinyin 的 _merge_erhua），
    以便播种时音节数与汉字数对齐（哪儿 = ['nǎ','r'] 对应 2 个字）。
    """
    return [_syl_to_diacritic(s) for s in numbered.split()]


def seed_overrides(cedict, manual_overrides):
    """把 CC-CEDICT 的轻声/儿化词 + 人工多音字 播种进 pypinyin。返回播种词数。

    仅对“CEDICT 拼音（含轻声/儿化）与 pypinyin 默认不同”的词播种，修正批量轻声。
    """
    phrases = {}
    for word, numbered in cedict.pinyin_num.items():
        # 只播种多字词：单字多音字（要/长/行…）交给 pypinyin 的上下文判断，
        # 避免用 CEDICT 首义项覆盖掉上下文正确的读音（如 我要 的 要=yào）。
        if len(word) < 2 or not all(_HAN.match(c) for c in word):
            continue
        toned = cedict_word_toned(numbered)
        default = lazy_pinyin(word, style=Style.TONE)
        # 音节数须与汉字数对齐（异常/非常规注音跳过）
        if len(toned) != len(word):
            continue
        if toned != default:
            phrases[word] = [[t] for t in toned]
    # 人工 overrides 覆盖在最后，优先级最高
    for word, seq in (manual_overrides or {}).items():
        phrases[word] = seq
    if phrases:
        load_phrases_dict(phrases)
    return len(phrases)


def sentence_char_pinyin(text):
    """句级拼音（上下文感知），返回 {字符索引: 音节}。"""
    # lazy_pinyin 把连续的非汉字（如 ”，）合并成一个元素原样返回，
    # 所以不能按下标一一对应，要按元素消耗的字符数推进。
    syls = lazy_pinyin(text, style=Style.TONE)
    out = {}
    i = 0
    for s in syls:
        if i >= len(text):
            break
        if _HAN.match(text[i]):
            out[i] = s
            i += 1
        else:
            i += len(s)
    for j, ch in enumerate(text):
        if _HAN.match(ch) and j not in out:
            out[j] = lazy_pinyin(ch, style=Style.TONE)[0]
    return out


def _merge_erhua(syls):
    out = []
    for s in syls:
        if s == 'r' and out:
            out[-1] += s
        else:
            out.append(s)
    return out


def token_pinyin(text, tokens, char_map):
    """按字对齐把句级音节分配到每个词，返回 [词拼音字符串]，并合并儿化。"""
    result = []
    cursor = 0
    for w in tokens:
        start = text.find(w, cursor)
        if start < 0:
            start = cursor
        cursor = start + len(w)
        syls = [char_map[j] for j in range(start, start + len(w)) if j in char_map]
        result.append(' '.join(_merge_erhua(syls)))
    return result


def sentence_pinyin(char_map):
    """整句拼音字符串（过滤标点、合并儿化）。"""
    syls = [char_map[j] for j in sorted(char_map)]
    return ' '.join(_merge_erhua(syls))


def numbered_pinyin(text):
    """数字调号整句拼音（便于程序处理/教学）。"""
    syls = lazy_pinyin(text, style=Style.TONE3, neutral_tone_with_five=True)
    return ' '.join(s for s in syls if _HAN.match(s[0]) or s[0].isalpha())


def numbered_from_toned(text):
    """Keep advanced numbered pinyin aligned with reviewed token readings."""
    from pypinyin.contrib.tone_convert import to_tone3
    return ' '.join(to_tone3(s, neutral_tone_with_five=True) for s in text.split())


_MARKS = '̄́̌̀'
_NUMERALS = set('零一二三四五六七八九十百千万两')


def _tone(syl):
    import unicodedata
    d = unicodedata.normalize('NFD', syl)
    return next((i for i, m in enumerate(_MARKS, 1) if m in d), 0)


def _char_syllables(text, words, pys):
    """把每个词的音节对到原句的字位置，返回 [(字位置, 词序号, 音节序号)]；儿化音节同时覆盖“儿”。"""
    out, cursor = [], 0
    for wi, (w, py) in enumerate(zip(words, pys)):
        start = text.find(w, cursor)
        if start < 0:
            continue
        cursor = start + len(w)
        syls = py.split() if py else []
        hans = [i for i, ch in enumerate(w) if _HAN.match(ch)]
        si = 0
        for k in hans:
            if si >= len(syls):
                break
            if w[k] == '儿' and si > 0 and syls[si - 1].endswith('r') and len(syls) < len(hans):
                continue
            out.append((start + k, wi, si))
            si += 1
    return out


def apply_yi_bu_sandhi(text, words, pys):
    """按 GF0025-2021 词表的注音体例标「一」「不」的变调。

    - 不：四声（含本调为四声的轻声字）前标 bú；A不A 中间标轻声 bu；其余保持原样。
    - 一：序数/号码（第一、初一、十一、一月、一号、一楼、一年级、一等奖、一一）和词末的「一」保持 yī；
      重叠动词中间（看一看）标轻声 yi；其余四声前 yí、一二三声前 yì。
    只改本调写法的 yī / bù，已标轻声或已变调的不动。
    """
    pys = list(pys)
    cells = _char_syllables(text, words, pys)
    at = {pos: (wi, si) for pos, wi, si in cells}

    def syl(pos):
        wi, si = at[pos]
        return pys[wi].split()[si]

    def next_tone(pos):
        if pos + 1 not in at:
            return None
        t = _tone(syl(pos + 1))
        return t or _tone(lazy_pinyin(text[pos + 1], style=Style.TONE)[0])

    def put(pos, value):
        wi, si = at[pos]
        parts = pys[wi].split()
        parts[si] = value
        pys[wi] = ' '.join(parts)

    for pos, wi, si in cells:
        ch = text[pos]
        if ch not in '一不':
            continue
        cur = syl(pos)
        prev = text[pos - 1] if pos else ''
        nxt = text[pos + 1] if pos + 1 < len(text) else ''
        w = words[wi]
        if ch == '不':
            if cur != 'bù':
                continue
            a_bu_a = w == '不' or not w.startswith('不') or (len(w) == 2 and w[1] == prev)
            idiom = text[pos - 2:pos - 1] in ('一', '爱') or prev + ch + nxt == '时不时'  # 一动不动、爱理不理、时不时：不读本调
            if prev and prev == nxt and _HAN.match(prev) and a_bu_a and not idiom:
                put(pos, 'bu')
            elif next_tone(pos) == 4:
                put(pos, 'bú')
            continue
        if cur != 'yī':
            continue
        if len(w) > 1 and w.endswith('一') and w.index('一') == len(w) - 1 and w != '另一':
            continue  # 统一、唯一、之一、第一
        if prev and (prev in '第初独' or prev in _NUMERALS and prev != '一' or prev == '一'):
            continue
        if prev == '比' and pos >= 2 and text[pos - 2] in _NUMERALS:
            continue  # 比分：三比一
        if not nxt or nxt == '一' or nxt in _NUMERALS and nxt not in '百千万':
            continue
        if nxt in '月号日楼' or text[pos + 1:pos + 3] in ('年级', '等奖'):
            continue
        if w == '一' and prev and prev == nxt and _HAN.match(prev) and text[pos - 2:pos - 1] != '一':
            put(pos, 'yi')
            continue
        t = next_tone(pos)
        if t == 4:
            put(pos, 'yí')
        elif t in (1, 2, 3):
            put(pos, 'yì')
    return pys
