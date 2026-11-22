#!/usr/bin/env python3
"""Build a portable Hugging Face dataset folder from the canonical dist/."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
JSONL_RELATIVE_PATH = Path("data") / "train.jsonl"
PARQUET_RELATIVE_PATH = Path("data") / "train.parquet"
# The Hub allows at most 10,000 files per directory. Levels 1-6 keep their
# original audio/ paths; the 7-9 band (hsk_level 7, 11,154 files) lives in
# audio/hsk7/<range>/, one folder per 1,000 sentence numbers.
HUB_AUDIO_SUBDIR_LEVELS = {7: "hsk7"}
HUB_MAX_FILES_PER_DIR = 10_000


def hub_audio_path(record: dict, path: str) -> str:
    """Map a canonical dist/ audio path to its location in the Hub export."""
    subdir = HUB_AUDIO_SUBDIR_LEVELS.get(record["hsk_level"])
    if subdir is None:
        return path
    folder, name = path.rsplit("/", 1)
    start = int(record["id"].rsplit("-", 1)[1]) // 1000 * 1000
    return f"{folder}/{subdir}/{start:04d}-{start + 999:04d}/{name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "release" / "huggingface")
    parser.add_argument("--audio-mode", choices=("copy", "hardlink", "none"), default="copy")
    parser.add_argument("--force", action="store_true", help="replace an existing export directory")
    return parser.parse_args()


def validate_jsonl(path: Path, expected_records: int) -> None:
    """Fail the export before upload if the Viewer input is not valid JSON Lines."""
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = json.loads(line)
            if not isinstance(record, dict) or not record.get("id"):
                raise SystemExit(f"Invalid record at {path}:{line_number}")
            count += 1
    if count != expected_records:
        raise SystemExit(f"Expected {expected_records:,} JSONL records; found {count:,}")


def write_parquet(records: list[dict], path: Path) -> None:
    """Write native Parquet so the Hub Viewer does not depend on auto-conversion."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ModuleNotFoundError as error:
        raise SystemExit(
            "Parquet export requires pyarrow. Run with: "
            "uv run --with pyarrow python scripts/export_huggingface.py ..."
        ) from error

    table = pa.Table.from_pylist(records)
    if table.num_rows != len(records):
        raise SystemExit(f"Expected {len(records):,} Parquet rows; found {table.num_rows:,}")
    pq.write_table(table, path, compression="zstd")


def main() -> None:
    args = parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        if not args.force:
            raise SystemExit(f"{out} is not empty; pass --force to replace it")
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True, exist_ok=True)

    records = json.loads((ROOT / "dist" / "sentences.json").read_text(encoding="utf-8"))
    if sum(r["hsk_level"] <= 6 for r in records) != 4354 or len({r["id"] for r in records}) != len(records):
        raise SystemExit("Expected 4,354 preserved level 1–6 records and unique IDs")
    levels = Counter(record["hsk_level"] for record in records)
    exported_records = []
    for record in records:
        audio = {speed: hub_audio_path(record, path) for speed, path in record["audio"].items()}
        exported_records.append({
            **record,
            "audio": audio,
            "audio_normal": audio["normal"],
            "audio_slow": audio["slow"],
        })
    jsonl_data = out / JSONL_RELATIVE_PATH
    with jsonl_data.open("w", encoding="utf-8") as handle:
        for exported in exported_records:
            handle.write(json.dumps(exported, ensure_ascii=False, separators=(",", ":")) + "\n")
    validate_jsonl(jsonl_data, len(records))
    write_parquet(exported_records, out / PARQUET_RELATIVE_PATH)

    audio_files = list((ROOT / "dist" / "audio").glob("*.mp3"))
    if len(audio_files) != 2 * len(records):
        raise SystemExit(f"Expected {2 * len(records):,} MP3 files; found {len(audio_files)}")
    placement = {
        source: target
        for original, exported in zip(records, exported_records)
        for speed in ("normal", "slow")
        for source, target in [(original["audio"][speed], exported["audio"][speed])]
    }
    if {Path(source).name for source in placement} != {path.name for path in audio_files}:
        raise SystemExit("dist/audio does not match the audio paths in sentences.json")
    per_dir = Counter(target.rsplit("/", 1)[0] for target in placement.values())
    if max(per_dir.values()) > HUB_MAX_FILES_PER_DIR:
        raise SystemExit(f"Hub directory limit exceeded: {dict(per_dir)}")
    if args.audio_mode != "none":
        copy_function = os.link if args.audio_mode == "hardlink" else shutil.copy2
        for source, target in placement.items():
            (out / target).parent.mkdir(parents=True, exist_ok=True)
            copy_function(ROOT / "dist" / source, out / target)

    shutil.copy2(ROOT / "huggingface" / "README.md", out / "README.md")
    shutil.copy2(ROOT / "ATTRIBUTION.md", out / "ATTRIBUTION.md")
    shutil.copy2(ROOT / "dist" / "exam_vocab_metadata.json", out / "exam_vocab_metadata.json")
    metadata = {
        "version": "1.2.1",
        "records": len(records),
        "audio_files": len(audio_files),
        "audio_directories": dict(sorted(per_dir.items())),
        "audio_included": args.audio_mode != "none",
        "viewer_data": PARQUET_RELATIVE_PATH.as_posix(),
        "source_data": JSONL_RELATIVE_PATH.as_posix(),
        "levels": {str(level): levels[level] for level in sorted(levels)},
        "license": "CC-BY-SA-4.0",
    }
    (out / "export-manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(
        f"exported {len(records):,} validated JSONL + Parquet records and "
        f"{len(audio_files):,} audio references → {out}"
    )


if __name__ == "__main__":
    main()
