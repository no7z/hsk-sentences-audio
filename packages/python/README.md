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
