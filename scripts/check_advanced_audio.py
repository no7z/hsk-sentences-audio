"""Probe/decode advanced MP3 pairs and optionally flag ASR/text mismatches.

Use the existing CosyVoice WSL environment for --asr; only a cached Whisper
model is accepted. This is a triage tool, not a substitute for listening review.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def han(text):
    return ''.join(re.findall('[一-鿿]', text))


def character_error_rate(expected, actual):
    a, b = han(expected), han(actual)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        row = [i]
        for j, y in enumerate(b, 1):
            row.append(min(row[-1] + 1, prev[j] + 1, prev[j - 1] + (x != y)))
        prev = row
    return round(prev[-1] / max(1, len(a)), 4)


def check(records, asr_model=None):
    checks = []
    for r in records:
        item = {"id": r["id"], "chinese": r["chinese"], "files": {}, "flags": []}
        for speed in ("normal", "slow"):
            path = ROOT / "dist" / r["audio"][speed]
            if not path.exists():
                item["flags"].append(f"missing_{speed}")
                continue
            try:
                probe = json.loads(subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))
                stream = next(s for s in probe["streams"] if s["codec_type"] == "audio")
                duration = float(probe["format"]["duration"])
                data = {"duration_seconds": duration, "sample_rate": int(stream["sample_rate"]),
                        "channels": stream["channels"], "codec": stream["codec_name"],
                        "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest()}
                subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"], check=True, capture_output=True)
                if data["sample_rate"] != 24000 or data["channels"] != 1 or data["codec"] != "mp3":
                    item["flags"].append(f"unexpected_format_{speed}")
                if duration < 1 or duration > 30:
                    item["flags"].append(f"unusual_duration_{speed}")
                if asr_model:
                    result = asr_model.transcribe(str(path), language="zh", temperature=0.0,
                                                 condition_on_previous_text=False,
                                                 initial_prompt="请用简体中文转写。", verbose=False)
                    data["asr"] = result["text"].strip()
                    data["character_error_rate"] = character_error_rate(r["chinese"], data["asr"])
                    if data["character_error_rate"] > 0.15:
                        item["flags"].append(f"asr_mismatch_{speed}")
                item["files"][speed] = data
            except (subprocess.CalledProcessError, KeyError, StopIteration, ValueError) as error:
                item["flags"].append(f"decode_failed_{speed}: {error}")
        if all(s in item["files"] for s in ("normal", "slow")):
            ratio = item["files"]["slow"]["duration_seconds"] / item["files"]["normal"]["duration_seconds"]
            item["slow_normal_duration_ratio"] = round(ratio, 4)
            if not 1.18 <= ratio <= 1.35:
                item["flags"].append("speed_ratio_review")
        checks.append(item)
        print(f"{r['id']}: {','.join(item['flags']) or 'ok'}", flush=True)
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asr", action="store_true")
    ap.add_argument("--asr-model", default="small")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg and ffprobe are required")
    records = [r for r in json.loads((ROOT / "dist/sentences.json").read_text(encoding="utf-8")) if r["hsk_level"] == 7]
    if args.ids:
        records = [r for r in records if r["id"] in args.ids]
        if {r["id"] for r in records} != set(args.ids):
            raise SystemExit("Unknown requested sentence ID")
    if args.limit is not None:
        if args.limit <= 0:
            raise SystemExit("--limit must be positive")
        records = records[:args.limit]
    model = None
    if args.asr:
        cached = Path.home() / ".cache/whisper" / f"{args.asr_model}.pt"
        if not cached.is_file():
            raise SystemExit(f"Cached model required; will not download: {cached}")
        import whisper
        model = whisper.load_model(str(cached))
    checks = check(records, model)
    ratios = [c["slow_normal_duration_ratio"] for c in checks if "slow_normal_duration_ratio" in c]
    result = {"model": args.asr_model if model else None, "sentences_checked": len(checks),
              "audio_files_checked": sum(len(c["files"]) for c in checks),
              "slow_methods": dict(Counter(r.get("audio_meta", {}).get("slow_method", "unspecified") for r in records)),
              "flagged_sentences": sum(bool(c["flags"]) for c in checks),
              "flags": dict(Counter(f for c in checks for f in c["flags"])),
              "duration_ratio_summary": {"min": min(ratios), "median": statistics.median(ratios), "max": max(ratios)} if ratios else None,
              "listening_review": "pending",
              "limitations": "ASR is a screening signal, not proof of pronunciation or naturalness; listening review remains required.",
              "checks": checks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, ensure_ascii=False, indent=2))
    if result["flagged_sentences"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
