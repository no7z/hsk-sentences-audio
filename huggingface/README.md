---
language:
- zh
- en
license: cc-by-sa-4.0
task_categories:
- text-to-speech
- translation
pretty_name: HSK Sentences Audio
size_categories:
- 1K<n<10K
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train.parquet
tags:
- hsk
- mandarin
- pinyin
- language-learning
- synthetic-audio
---

# HSK Sentences Audio

4,354 Chinese sentences authored against GF0025-2021 levels 1–6, with
pinyin, English translations, per-word glosses, grammar tags, and normal/slow
synthetic speech. The complete export contains 8,708 MP3 files.

## Dataset structure

The Viewer reads native Parquet from `data/train.parquet`, avoiding a dependency
on Hugging Face's JSON-to-Parquet conversion service. The same 4,354 records are
also available as validated JSON Lines in `data/train.jsonl`. Important fields:

- `id`, `hsk_level`, `topic`, `sentence_type`
- `exam_vocab_level_2025`: nullable vocabulary-only estimate under the 2025 exam syllabus; 7 means the combined 7–9 band, not an official sentence grade. Grammar and senses/POS are not assessed.
- `chinese`, `traditional`, `pinyin`, `pinyin_numbered`
- `translation.en`, token-level `word` / `pinyin` / `gloss_en`
- `grammar_points`, official `grammar_tags`
- `audio.normal`, `audio.slow`, and synthesis metadata
- convenience fields `audio_normal` and `audio_slow` for dataset viewers

Sentence counts by level: HSK 1: 281; HSK 2: 538; HSK 3: 727; HSK 4:
801; HSK 5: 965; HSK 6: 1,042.

## Intended uses and limits

Suitable for flashcards, shadowing, listening practice, SRS, pronunciation
interfaces, and Chinese-learning research prototypes. Audio is synthetic
(CosyVoice2-0.5B, `zh-female-studio`) and should be disclosed as such in
downstream products. The dataset is educational material, not an assessment
instrument or a substitute for native-speaker review.

## License and attribution

Dataset: CC-BY-SA-4.0. Glosses and some pinyin data derive from CC-CEDICT
(CC-BY-SA); audio was synthesized with Apache-2.0 CosyVoice2. See
`ATTRIBUTION.md` in this dataset export for detailed provenance.
