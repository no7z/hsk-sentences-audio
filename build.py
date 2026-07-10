# -*- coding: utf-8 -*-
"""hsk-sentences-audio 构建管线。

源句子(data/sentences/*.yaml) → 结构化数据(dist/sentences.json) + 音频(dist/audio/*.mp3)。

流程：
  1. 加载 CC-CEDICT，用其轻声/儿化词 + 人工 overrides 播种 pypinyin
  2. 逐句：CC-CEDICT 最大匹配分词 → 句级拼音按字对齐到词 → opencc 繁体 → CEDICT 词义
  3. CosyVoice2 合成常速/慢速音频 + 后处理（裁 onset + 淡入）
  4. 自动标红多音字/未收录词，写 dist/review_flags.txt 供人工秒批

用法：
  python build.py --level 1                 # 全量构建（含音频）
  python build.py --level 1 --no-audio      # 只出文本数据（快速校对拼音）
"""
import argparse
import json
from pathlib import Path

import yaml
from opencc import OpenCC

from lib.cedict import Cedict
from lib.segment import segment
from lib.flags import review_flags
from lib import pinyin as P

ROOT = Path(__file__).resolve().parent
CEDICT_PATH = ROOT / "data/cedict/cedict.txt"
OVERRIDES_PATH = ROOT / "data/overrides.json"
DIST = ROOT / "dist"

# yaml 分区注释 → 规范化主题 slug
TOPIC_MAP = {
    "问候与礼貌": "greetings", "人称与身份": "identity", "家庭": "family",
    "数字、年龄、量": "numbers", "时间与日期": "time", "日常动作": "daily_actions",
    "学校与工作": "school_work", "地点与方位": "location", "出行与交通": "transport",
    "购物与钱": "shopping", "饮食": "food", "天气与状态": "weather_state",
    "能愿、提问、判断": "questions", "物品与其他": "objects_misc",
    "健康与身体": "health_body", "运动与文娱": "sports_leisure",
    "情感与观点": "feelings", "自然与动物": "nature",
}


def parse_topics(yaml_path):
    """从原始 yaml 的 `# —— X ——` 分区注释提取每句的主题（按句子出现顺序对齐）。

    句子条目内显式的 `topic:` 字段优先于分区注释。补充区（覆盖补充）无规范主题，
    返回 None，由条目内显式 topic 兜底。
    """
    import re
    topics = []
    current = None
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*# —— (.+?)（?[一二三]?）? ——', line)
        if m:
            current = TOPIC_MAP.get(m.group(1).strip())
            continue
        if re.match(r'\s*- (\{|chinese:)', line):
            topics.append(current)
    return topics


def sentence_type(zh):
    """句型：question / imperative / statement。"""
    if "？" in zh:
        return "question"
    if zh.startswith(("请", "别")) or zh.rstrip("。！").endswith("吧"):
        return "imperative"
    return "statement"


# 语法点检测：规则来自官方语法点注册表 data/grammar_points.json（由
# scripts/gen_grammar_registry.py 生成，检测正则人工维护于该脚本的 PATTERNS）。
# grammar_tags 的值是官方编号（如 "1-45" = 【一45】用"吗"提问）。
import re as _re

def load_grammar_rules():
    reg = json.loads((ROOT / "data/grammar_points.json").read_text(encoding="utf-8"))
    rules = []
    for e in reg:
        if e.get("pattern"):
            pat = _re.compile(e["pattern"])
            exc = _re.compile(e["exclude"]) if e.get("exclude") else None
            rules.append((e["id"], pat, exc))
    return rules


GRAMMAR_RULES = load_grammar_rules()


def detect_grammar(zh):
    return [pid for pid, pat, exc in GRAMMAR_RULES
            if pat.search(zh) and not (exc and exc.search(zh))]


def load_hsk_vocab():
    """全级 HSK 词表（用于分词回拆）。"""
    v = set()
    for f in (ROOT / "data/hsk_wordlist").glob("new_*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            s = e.get("simplified")
            if s:
                v.add(s)
    return v


def build(level, with_audio=True):
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    cedict = Cedict(CEDICT_PATH)
    seeded = P.seed_overrides(cedict, overrides.get("polyphone", {}))
    print(f"CC-CEDICT: {len(cedict.vocab)} 词；播种 pypinyin 修正 {seeded} 条")

    seg_exceptions = overrides.get("segmentation", {})
    seg_blocklist = overrides.get("seg_blocklist", [])
    hsk_vocab = load_hsk_vocab()
    token_py_override = overrides.get("token_pinyin", {})
    gloss_override = overrides.get("gloss", {})
    cc = OpenCC("s2t")

    yaml_path = ROOT / f"data/sentences/hsk{level}.yaml"
    src = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    sentences = src["sentences"]
    section_topics = parse_topics(yaml_path)
    if len(section_topics) != len(sentences):
        print(f"⚠️ 主题对齐失败（{len(section_topics)} vs {len(sentences)}），topic 仅用条目内显式值")
        section_topics = [None] * len(sentences)

    tts = None
    if with_audio:
        ref_wav = ROOT / "data/reference/ref_female.wav"
        ref_txt = ROOT / "data/reference/ref_female.txt"
        if not ref_wav.exists():
            raise SystemExit("缺少参考音频，请先运行： python scripts/make_reference.py")
        from lib.tts import CosyVoiceTTS
        tts = CosyVoiceTTS(ref_wav, ref_txt.read_text(encoding="utf-8").strip())
        (DIST / "audio").mkdir(parents=True, exist_ok=True)

    records, review = [], []
    for idx, s in enumerate(sentences, 1):
        sid = f"hsk{level}-{idx:04d}"
        zh = s["chinese"]
        topic = s.get("topic") or section_topics[idx - 1] or "misc"
        tokens_w = segment(zh, hsk_vocab, seg_exceptions, seg_blocklist)
        char_map = P.sentence_char_pinyin(zh)
        tok_py = P.token_pinyin(zh, tokens_w, char_map)
        # 逐词拼音直接覆盖（审核沉淀层，命中即替换，不依赖 pypinyin 分词）
        tok_py = [token_py_override.get(w, py) for w, py in zip(tokens_w, tok_py)]
        tokens = [{"word": w, "pinyin": py,
                   "gloss_en": gloss_override.get(w, cedict.gloss.get(w, ""))}
                  for w, py in zip(tokens_w, tok_py)]

        rec = {
            "id": sid,
            "hsk_level": level,
            "topic": topic,
            "sentence_type": sentence_type(zh),
            "chinese": zh,
            "traditional": cc.convert(zh),
            "pinyin": " ".join(tok_py),   # 由（已覆盖的）逐词拼音拼接，保证与 tokens 一致
            "pinyin_numbered": P.numbered_pinyin(zh),
            "translation": {"en": s.get("en", "")},
            "tokens": tokens,
            "grammar_points": s.get("grammar", []),
            "grammar_tags": detect_grammar(zh),
            "audio": {"normal": f"audio/{sid}.mp3", "slow": f"audio/{sid}_slow.mp3"},
            "audio_meta": {"engine": "cosyvoice2-0.5B", "voice": "zh-female-studio",
                           "license": "Apache-2.0", "sample_rate": 24000},
        }
        review.extend(review_flags(sid, tokens, cedict.vocab))

        if tts:
            mp3_n = DIST / "audio" / f"{sid}.mp3"
            mp3_s = DIST / "audio" / f"{sid}_slow.mp3"
            # 断点续跑：两个音频都已存在则跳过（句子文本变更时请删除对应 mp3 重合成）
            if mp3_n.exists() and mp3_s.exists():
                pass
            else:
                tts.synth(zh, str(mp3_n), speed=1.0)
                tts.synth(zh, str(mp3_s), speed=0.8)
                print(f"  ♪ {sid}  {zh}")
        records.append(rec)

    DIST.mkdir(exist_ok=True)
    # 按级合并：保留其他等级的已有记录，仅替换本级
    merged = []
    sj = DIST / "sentences.json"
    if sj.exists():
        merged = [r for r in json.loads(sj.read_text(encoding="utf-8"))
                  if r.get("hsk_level") != level]
    merged.extend(records)
    merged.sort(key=lambda r: r["id"])
    sj.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIST / "review_flags.txt").write_text("\n".join(review), encoding="utf-8")
    print(f"\n完成：本级 {len(records)} 句（合计 {len(merged)}）-> dist/sentences.json；标红 {len(review)} 条")

    # 生成自包含网页产物（data.js / index.html / setup.html）
    try:
        import subprocess
        subprocess.run([__import__("sys").executable,
                        str(ROOT / "scripts/build_web.py")], check=True)
    except Exception as e:
        print("（web 生成跳过：", e, "）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()
    build(args.level, with_audio=not args.no_audio)
