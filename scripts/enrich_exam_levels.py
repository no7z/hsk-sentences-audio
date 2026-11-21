#!/usr/bin/env python3
"""Backfill only the additive exam vocabulary estimate, preserving all other data.

Install requirements-exam.txt, then run with --write. Without --write this
checks that both the canonical data and its reproducibility metadata are current.
"""
import argparse
from collections import Counter
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.exam_level import exam_level  # noqa: E402

FIELD = "exam_vocab_level_2025"
REVIEWED_VERSION = "0.3.0"


def enrich_records(records):
    # Every authored level, including the GF0025-2021 7-9 band, gets the same
    # vocabulary-only estimate against the 2025 exam syllabus.
    return [{**record, FIELD: exam_level([t["word"] for t in record["tokens"]])} for record in records]


def metadata(records):
    legacy = [{k: v for k, v in r.items() if k != FIELD} for r in records]
    legacy_bytes = json.dumps(legacy, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")).encode()
    return {
        "field": FIELD,
        "standard": "HSK examination syllabus, published 2025-11",
        "official_source": "https://www.chinesetest.cn/Development?lang=cn",
        "syllabus_pdf": "https://hsk.cn-bj.ufileos.com/3.0/新版HSK考试大纲1219.pdf",
        "method": "max token word level; recognition-character fallback for unlisted words",
        "limitations": "Not an official sentence grade; no grammar, sense or POS disambiguation. Homographs use their lowest listed level.",
        "ungraded": "null when there is no gradeable Han text, the tables are missing, or any fallback Han character is unlisted",
        "high_band": {"value": 7, "label": "7-9"},
        "table_package": "hsk30",
        "table_package_version": version("hsk30"),
        "table_sha256": {name: sha256(files("hsk30").joinpath("data", name).read_bytes()).hexdigest()
                         for name in ("hsk2025_words.tsv", "hsk2025_chars.tsv")},
        "records": len(records),
        "legacy_records_sha256": sha256(legacy_bytes).hexdigest(),
        "distribution": dict(sorted(Counter(str(r[FIELD]) for r in records).items())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        actual_version = version("hsk30")
    except Exception as error:
        raise SystemExit("Install requirements-exam.txt before enriching data") from error
    if actual_version != REVIEWED_VERSION:
        raise SystemExit(f"Expected hsk30=={REVIEWED_VERSION}; found {actual_version}")
    path = ROOT / "dist" / "sentences.json"
    meta_path = path.with_name("exam_vocab_metadata.json")
    records = json.loads(path.read_text(encoding="utf-8"))
    enriched = enrich_records(records)
    info = metadata(enriched)
    if args.write:
        path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        meta_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    elif records != enriched or not meta_path.exists() or json.loads(meta_path.read_text(encoding="utf-8")) != info:
        raise SystemExit("Exam vocabulary data/metadata are stale; rerun with --write")
    print(json.dumps({"records": len(records), "distribution": info["distribution"],
                      "legacy_records_sha256": info["legacy_records_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
