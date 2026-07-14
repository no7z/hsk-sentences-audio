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
