from pathlib import Path
import json
import shutil

from setuptools import setup


PACKAGE_DIR = Path(__file__).resolve().parent
SOURCE = PACKAGE_DIR.parents[1] / "dist" / "sentences.json"
DESTINATION = PACKAGE_DIR / "src" / "hsk_sentences_audio" / "data" / "sentences.json"

if SOURCE.exists():
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    if len(records) != 4354:
        raise RuntimeError(f"Expected 4,354 canonical records; found {len(records)}")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, DESTINATION)
elif not DESTINATION.exists():
    raise RuntimeError("sentences.json is missing; build this package from the repository root")

setup()
