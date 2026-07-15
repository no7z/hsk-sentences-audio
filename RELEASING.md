# Distribution release checklist

The canonical source remains `dist/sentences.json` plus `dist/audio/`. Package
payloads are generated from it so the 4,354 records cannot silently drift.

## Verify everything

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

# Hugging Face staging folder; hardlinks avoid another 169 MB local copy.
# pyarrow writes native Parquet for the Dataset Viewer.
uv run --with pyarrow python scripts/export_huggingface.py --audio-mode hardlink --force
```

Expected invariants:

- npm unpacked size: about 6.4 MB; no MP3 files
- Python wheel: about 0.9 MB compressed; `load_sentences()` returns 4,354
- Hugging Face: 4,354 rows in native `data/train.parquet`, the same validated
  records in `data/train.jsonl`, and 8,708 MP3 files
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
loaders return 4,354 records. Dataset consumers must retain the CC-BY-SA-4.0
attribution in `ATTRIBUTION.md`; audio should be disclosed as synthetic.
