# Distribution release checklist

The canonical source remains `dist/sentences.json` plus `dist/audio/`. Package
payloads are generated from it so the records cannot silently drift. Levels
1–6 keep the 4,354 frozen records; the 7–9 band adds 5,577 (9,931 in total).

## Verify everything

Before rebuilding consumer payloads, install `requirements-exam.txt` and run
`python scripts/enrich_exam_levels.py --write`, then run it without `--write`
to verify the additive exam vocabulary field and provenance. Rebuild the web
artifacts with `python scripts/build_web.py`. Existing authored levels, IDs,
text, tokens and audio paths must remain unchanged.

```bash
# npm loader + exact tarball contents
npm --prefix packages/npm test
npm --prefix packages/npm pack --dry-run

# Python wheel (builds the JSON payload from canonical dist/)
python packages/python/scripts/prepare.py
python -m unittest discover packages/python/tests
python -m pip wheel packages/python --no-deps --wheel-dir release/python

# React consumer integration
npm --prefix examples/react install
npm --prefix examples/react run build

# Hugging Face staging folder; hardlinks avoid another ~610 MB local copy.
# pyarrow writes native Parquet for the Dataset Viewer.
uv run --with pyarrow python scripts/export_huggingface.py --audio-mode hardlink --force
```

Expected invariants:

- npm unpacked size: about 21 MB; no MP3 files
- Python wheel: a few MB compressed; `load_sentences()` returns 9,931
- Hugging Face: 9,931 rows in native `data/train.parquet`, the same validated
  records in `data/train.jsonl`, and 19,862 MP3 files
- React production build includes one hosted `sentences.json`, not a duplicate
  bundled into JavaScript

## Publish (requires registry credentials)

Publishing changes external state and is deliberately not part of the build.
After reviewing the generated artifacts and confirming the names are available:

```bash
# npm — requires `npm login`
cd packages/npm
npm publish --access public

# PyPI — requires a token configured for twine
python -m pip install build twine
python -m build packages/python --outdir release/python
python -m twine upload release/python/*

# Hugging Face — authenticate with the HF CLI, then upload. This refreshes the
# Viewer configuration and points it at native data/train.parquet.
hf upload no7z/hsk-sentences-audio release/huggingface . --repo-type dataset
```

Tag the repository only after all three public pages resolve and their sample
loaders return 9,931 records. Dataset consumers must retain the CC-BY-SA-4.0
attribution in `ATTRIBUTION.md`; audio should be disclosed as synthetic.
