#!/usr/bin/env python3
"""Copy the canonical JSON into the Python package staging directory."""

import json
from pathlib import Path
import shutil


PACKAGE_DIR = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE_DIR.parents[1] / "dist" / "sentences.json"
DESTINATION = PACKAGE_DIR / "src" / "hsk_sentences_audio" / "data" / "sentences.json"
records = json.loads(SOURCE.read_text(encoding="utf-8"))
if len(records) != 4354:
    raise SystemExit(f"Expected 4,354 canonical records; found {len(records)}")
DESTINATION.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(SOURCE, DESTINATION)
print(f"prepared {len(records):,} records → {DESTINATION}")
