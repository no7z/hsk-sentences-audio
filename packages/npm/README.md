# hsk-sentences-audio

Typed, dependency-free loader for the
[no7z/hsk-sentences-audio](https://github.com/no7z/hsk-sentences-audio)
dataset: 4,354 HSK 3.0 graded sentences with pinyin, English translations,
per-word glosses, grammar tags, and normal/slow audio paths.

```js
import { loadSentences, filterSentences, audioUrl } from "hsk-sentences-audio";

const all = await loadSentences();
const cards = filterSentences(all, { level: 2, topic: "food", limit: 20 });
console.log(cards[0].chinese, audioUrl(cards[0], { speed: "slow" }));
```

The npm tarball contains the 6.1 MB JSON dataset, not 169 MB of MP3s. Audio
URLs default to the GitHub-hosted `dist/` assets; pass `baseUrl` to use your own
CDN. In a browser, you can host the JSON yourself and pass `{ url }` to
`loadSentences` (see the repository's React example).

Code is MIT. The packaged dataset is CC-BY-SA-4.0; retain attribution when
redistributing it. See the repository's `ATTRIBUTION.md` for full provenance.

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
