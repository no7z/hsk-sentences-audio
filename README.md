# hsk-sentences-audio

[中文](README.zh-CN.md) | **English**

> HSK-graded Chinese sentence dataset: sentences + pinyin + English translations + per-word glosses + official grammar-point tags + normal/slow audio. Graded against the official HSK 3.0 standard. Ready-to-use JSON + MP3.

A ready-made data layer for Chinese-learning apps. Every sentence is a self-contained structured record with dual-speed audio — drop it straight into flashcards, shadowing, listening practice, or SRS apps.

## Current scale

| Level | Sentences | Wordlist coverage | Out-of-level words |
|---|---|---|---|
| HSK 1 | 281 | 94% (480/506 words) | 0 |
| HSK 2 | 538 | 100% (750/750 words) | 0 |
| HSK 3 | 727 | 99% (950/953 words) | 0 |
| HSK 4 | 801 | 98% (956/972 words) | 0 |
| HSK 5 | 965 | 98% (1045/1059 words) | 0 |
| HSK 6 | 1042 | 99% (1112/1123 words) | 0 |
| **Total** | **4354** | — | **0** |

Covers the complete **six official bands (levels 1–6)** of HSK 3.0, elementary through advanced. Companion audio: **8,708 MP3s** (normal + slow speed per sentence, ~170 MB). The few uncovered words at each level are bound morphemes that cannot stand alone in natural sentences (e.g. 员/者); their compounds are all included.

Grading follows the official *Chinese Proficiency Grading Standards for International Chinese Language Education* (GF0025-2021, a.k.a. "HSK 3.0"): sentences at each level **use only vocabulary from that level and below** (zero out-of-level words) while systematically covering that level's wordlist — both properties are machine-checkable with the validator in this repo, not just a claim.

## What a record looks like

One record from `dist/sentences.json`:

```json
{
  "id": "hsk1-0002",
  "hsk_level": 1,
  "topic": "greetings",
  "sentence_type": "statement",
  "chinese": "你好，很高兴认识你。",
  "traditional": "你好，很高興認識你。",
  "pinyin": "nǐ hǎo hěn gāo xìng rèn shi nǐ",
  "pinyin_numbered": "ni3 hao3 hen3 gao1 xing4 ren4 shi5 ni3",
  "translation": { "en": "Hello, nice to meet you." },
  "tokens": [
    { "word": "很",   "pinyin": "hěn",     "gloss_en": "very; quite" },
    { "word": "高兴", "pinyin": "gāo xìng", "gloss_en": "happy; glad" },
    { "word": "认识", "pinyin": "rèn shi",  "gloss_en": "to know; to recognize" }
  ],
  "grammar_tags": ["1-09"],
  "audio": { "normal": "audio/hsk1-0002.mp3", "slow": "audio/hsk1-0002_slow.mp3" },
  "audio_meta": { "engine": "cosyvoice2-0.5B", "voice": "zh-female-studio",
                  "license": "Apache-2.0", "sample_rate": 24000 }
}
```

Field notes:

- **pinyin / tokens.pinyin** — neutral tones handled (认识 = rèn **shi**), context-sensitive polyphones (要 = yào), erhua (哪儿 = nǎr); sentence-level pinyin is guaranteed consistent with per-token pinyin
- **topic** — 18 themes (greetings / family / time / food / transport / health…)
- **sentence_type** — statement / question / imperative
- **grammar_tags** — official grammar-point IDs (e.g. `"1-09"` = 【一09】 degree adverbs); the full registry with official categories, levels and example sentences lives in `data/grammar_points.json`
- **audio** — normal + slow MP3s, synthesized locally (CosyVoice2, Apache-2.0) with onset-denoise post-processing; freely redistributable with the dataset

## Use it directly

- **Browse**: double-click `dist/index.html` — works offline, no server needed. Search plus four cross-linked facets (level / topic / sentence type / grammar point, counts update live), click to play audio
- **Integrate**: open `dist/setup.html` — one-click export to SQL (SQLite/PostgreSQL/MySQL), CSV, and Anki import files; copy-paste Swift / TypeScript / Kotlin data models; an "Ask your LLM" prompt generator (iOS SRS app / FastAPI backend / React practice page) with the full schema baked in
- **Consume programmatically**: read `dist/sentences.json` + `dist/audio/` directly

## Distribution packages

This repository now includes registry-ready, dependency-free loaders. The npm
tarball and Python wheel contain the 6.1 MB JSON dataset; the 169 MB audio set
is resolved lazily from configurable URLs.

```bash
# JavaScript / TypeScript
npm install hsk-sentences-audio

# Python
pip install hsk-sentences-audio
```

```js
import { loadSentences, filterSentences, audioUrl } from "hsk-sentences-audio";
const all = await loadSentences();
const cards = filterSentences(all, { level: 2, topic: "food", limit: 20 });
console.log(cards[0].chinese, audioUrl(cards[0], { speed: "slow" }));
```

```python
from hsk_sentences_audio import audio_url, iter_sentences
card = next(iter_sentences(level=2, topic="food"))
print(card["chinese"], audio_url(card, speed="slow"))
```

- npm: [hsk-sentences-audio](https://www.npmjs.com/package/hsk-sentences-audio)
  (source: [`packages/npm`](packages/npm))
- PyPI: [hsk-sentences-audio](https://pypi.org/project/hsk-sentences-audio/)
  (source: [`packages/python`](packages/python))
- Hugging Face: [no4gun/hsk-sentences-audio](https://huggingface.co/datasets/no4gun/hsk-sentences-audio)
- Minimal React integration: [`examples/react`](examples/react)
- Hugging Face dataset card + exporter: [`huggingface`](huggingface) and
  `python scripts/export_huggingface.py` (default includes all audio; use
  `--audio-mode none` for a text-only staging export)

See [`RELEASING.md`](RELEASING.md) for the verified release commands and
registry credential steps.

## Build from source

```bash
# 1. Text-pipeline dependencies
pip install -r requirements.txt

# 2. Download CC-CEDICT and the official HSK wordlists / grammar texts
python scripts/download_cedict.py
python scripts/download_hsk.py

# 3. Text-only build (proofread pinyin/segmentation, no TTS needed)
python build.py --level 1 --no-audio

# 4. Grading validation: out-of-level words + wordlist coverage
python scripts/hsk_validate.py --level 1

# 5. Audio synthesis (install CosyVoice separately, set COSYVOICE_REPO)
python scripts/make_reference.py     # generate the reference voice (once)
python build.py --level 1            # full build (resume-safe)
```

A machine with an NVIDIA GPU can handle audio synthesis alone (4–8× faster than CPU): `scripts/synth_audio.py` reads `dist/sentences.json` and fills in missing audio (resume-safe, auto CUDA/CPU), fully decoupled from the text pipeline.

## Quality machinery

- **Grading validation** (`scripts/hsk_validate.py`): word-by-word checks against the official wordlists — containment (flags any word above the target level; goal is zero) and coverage (share of the target level's wordlist used). "Conforms to HSK level X" is a number you can reproduce, not a slogan
- **Grammar-point registry** (`data/grammar_points.json`): all 413 official grammar points across levels 1–6 (ID / level / category / examples), 70 of them with automatic detection rules; the rules are protected by the regression suite in `scripts/test_grammar_rules.py` (every historical false positive is a permanent negative case)
- **Pinyin**: pypinyin for sentence-level context + CC-CEDICT-seeded bulk corrections for neutral tones/erhua + a manual override layer (`data/overrides.json`); text and audio share the same source
- **Segmentation**: jieba (HMM off) + re-splitting against the full HSK wordlist (automatically breaks up spurious merges like 坐地铁/很漂亮) + an exception table
- **Audio**: CosyVoice2-0.5B synthesized locally with a studio female reference voice; onset transients trimmed + fade-in. Synthetic voice — downstream apps should disclose it as such, per common practice
- **Review flow**: builds auto-flag polyphones/out-of-dictionary tokens (`dist/review_flags.txt`) → human confirms → fixes settle into `data/overrides.json`, applied forever after

## Adding sentences

Edit `data/sentences/hsk<level>.yaml`; each sentence needs only three fields:

```yaml
- { chinese: "你好，很高兴认识你。", en: "Hello, nice to meet you.", grammar: ["很 + adj"] }
```

Pinyin, traditional characters, segmentation, glosses, topic, sentence type, grammar tags and audio are all generated by the pipeline; run the validator once to confirm zero out-of-level words.

## License

- **Code**: MIT (see `LICENSE`)
- **Dataset (`dist/`)**: CC-BY-SA 4.0 (glosses and per-word pinyin contain CC-CEDICT-derived content; audio synthesized with Apache-2.0 CosyVoice2)
- Full sources and attribution in [ATTRIBUTION.md](ATTRIBUTION.md)
