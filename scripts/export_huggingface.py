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
    if len(records) != 4354:
        raise SystemExit(f"Expected 4,354 canonical records; found {len(records)}")
    levels = Counter(record["hsk_level"] for record in records)
    exported_records = [
        {
            **record,
            "audio_normal": record["audio"]["normal"],
            "audio_slow": record["audio"]["slow"],
        }
        for record in records
    ]
    jsonl_data = out / JSONL_RELATIVE_PATH
    with jsonl_data.open("w", encoding="utf-8") as handle:
        for exported in exported_records:
            handle.write(json.dumps(exported, ensure_ascii=False, separators=(",", ":")) + "\n")
    validate_jsonl(jsonl_data, len(records))
    write_parquet(exported_records, out / PARQUET_RELATIVE_PATH)

    audio_files = list((ROOT / "dist" / "audio").glob("*.mp3"))
    if len(audio_files) != 8708:
        raise SystemExit(f"Expected 8,708 MP3 files; found {len(audio_files)}")
    if args.audio_mode != "none":
        copy_function = os.link if args.audio_mode == "hardlink" else shutil.copy2
        shutil.copytree(ROOT / "dist" / "audio", out / "audio", copy_function=copy_function)

    shutil.copy2(ROOT / "huggingface" / "README.md", out / "README.md")
    shutil.copy2(ROOT / "ATTRIBUTION.md", out / "ATTRIBUTION.md")
    metadata = {
        "version": "1.0.0",
        "records": len(records),
        "audio_files": len(audio_files),
        "audio_included": args.audio_mode != "none",
        "viewer_data": str(PARQUET_RELATIVE_PATH),
        "source_data": str(JSONL_RELATIVE_PATH),
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
