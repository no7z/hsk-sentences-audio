# -*- coding: utf-8 -*-
"""chinese-sentences-audio 构建管线。

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


def build(level, with_audio=True):
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    cedict = Cedict(CEDICT_PATH)
    seeded = P.seed_overrides(cedict, overrides.get("polyphone", {}))
    print(f"CC-CEDICT: {len(cedict.vocab)} 词；播种 pypinyin 修正 {seeded} 条")

    seg_exceptions = overrides.get("segmentation", {})
    cc = OpenCC("s2t")

    src = yaml.safe_load((ROOT / f"data/sentences/hsk{level}.yaml").read_text(encoding="utf-8"))
    sentences = src["sentences"]

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
        tokens_w = segment(zh, cedict.vocab, seg_exceptions)
        char_map = P.sentence_char_pinyin(zh)
        tok_py = P.token_pinyin(zh, tokens_w, char_map)
        tokens = [{"word": w, "pinyin": py, "gloss_en": cedict.gloss.get(w, "")}
                  for w, py in zip(tokens_w, tok_py)]

        rec = {
            "id": sid,
            "hsk_level": level,
            "chinese": zh,
            "traditional": cc.convert(zh),
            "pinyin": P.sentence_pinyin(char_map),
            "pinyin_numbered": P.numbered_pinyin(zh),
            "translation": {"en": s.get("en", "")},
            "tokens": tokens,
            "grammar_points": s.get("grammar", []),
            "audio": {"normal": f"audio/{sid}.mp3", "slow": f"audio/{sid}_slow.mp3"},
            "audio_meta": {"engine": "cosyvoice2-0.5B", "voice": "zh-female-studio",
                           "license": "Apache-2.0", "sample_rate": 24000},
        }
        review.extend(review_flags(sid, tokens, cedict.vocab))

        if tts:
            tts.synth(zh, str(DIST / "audio" / f"{sid}.mp3"), speed=1.0)
            tts.synth(zh, str(DIST / "audio" / f"{sid}_slow.mp3"), speed=0.8)
            print(f"  ♪ {sid}  {zh}")
        records.append(rec)

    DIST.mkdir(exist_ok=True)
    (DIST / "sentences.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIST / "review_flags.txt").write_text("\n".join(review), encoding="utf-8")
    print(f"\n完成：{len(records)} 句 -> dist/sentences.json；标红 {len(review)} 条 -> dist/review_flags.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()
    build(args.level, with_audio=not args.no_audio)
