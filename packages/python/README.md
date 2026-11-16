# hsk-sentences-audio

Dependency-free Python loader for 4,354 HSK 3.0 graded Chinese sentences.

```python
from hsk_sentences_audio import audio_url, iter_sentences, load_sentences

print(len(load_sentences()))
card = next(iter_sentences(level=2, topic="food"))
print(card["chinese"], audio_url(card, speed="slow"))
```

The wheel contains the 6.1 MB JSON dataset, not the 169 MB audio collection.
Audio URLs default to the repository's hosted `dist/` assets; pass `base_url`
to use your own CDN.

Code is MIT. The packaged dataset is CC-BY-SA-4.0; retain attribution when
redistributing it. Full provenance is in the repository's `ATTRIBUTION.md`.

## Independent exam vocabulary estimates

The existing `hsk_level` keeps its GF0025-2021 meaning. The additive
`exam_vocab_level_2025` is a vocabulary-only estimate against the 2025 exam
syllabus; `7` means the combined 7–9 band, not an individual seventh level.
It does not assess grammar or disambiguate senses/POS. Older records may omit
it; unavailable or incomplete estimates are `null`.

JavaScript: `filterSentences(records, { examVocabLevel: 3 })`.
Python: `iter_sentences(exam_vocab_level=3)`.
Both filters may be combined with the existing authored-level filter.

Maintainers can backfill canonical data without changing existing fields or
regenerating audio:

```bash
python -m pip install -r requirements-exam.txt
python scripts/enrich_exam_levels.py --write
python scripts/enrich_exam_levels.py
python scripts/build_web.py
```

The validation command fails on stale data/metadata or an unreviewed table
package version. Run it after rebuilding sentences. See
`dist/exam_vocab_metadata.json` and `ATTRIBUTION.md` in the source repository.
