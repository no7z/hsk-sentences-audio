from pathlib import Path
import json
import shutil

from setuptools import setup


PACKAGE_DIR = Path(__file__).resolve().parent
SOURCE = PACKAGE_DIR.parents[1] / "dist" / "sentences.json"
DESTINATION = PACKAGE_DIR / "src" / "hsk_sentences_audio" / "data" / "sentences.json"

if SOURCE.exists():
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    if sum(r["hsk_level"] <= 6 for r in records) != 4354 or len({r["id"] for r in records}) != len(records):
        raise RuntimeError("Expected 4,354 preserved level 1–6 records and unique IDs")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, DESTINATION)
    shutil.copy2(SOURCE.with_name("exam_vocab_metadata.json"), DESTINATION.with_name("exam_vocab_metadata.json"))
elif not DESTINATION.exists():
    raise RuntimeError("sentences.json is missing; build this package from the repository root")

setup()
