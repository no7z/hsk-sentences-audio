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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "release" / "huggingface")
    parser.add_argument("--audio-mode", choices=("copy", "hardlink", "none"), default="copy")
    parser.add_argument("--force", action="store_true", help="replace an existing export directory")
    return parser.parse_args()


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
    with (out / "data" / "sentences.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            exported = {
                **record,
                "audio_normal": record["audio"]["normal"],
                "audio_slow": record["audio"]["slow"],
            }
            handle.write(json.dumps(exported, ensure_ascii=False, separators=(",", ":")) + "\n")

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
        "levels": {str(level): levels[level] for level in sorted(levels)},
        "license": "CC-BY-SA-4.0",
    }
    (out / "dataset_info.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"exported {len(records):,} records and {len(audio_files):,} audio references → {out}")


if __name__ == "__main__":
    main()
