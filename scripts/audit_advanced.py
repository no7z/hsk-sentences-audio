"""Reproducible GF0025-2021 combined 7-9 spelling coverage and integrity audit.

No examination-syllabus classifications are used. Repeated source rows remain
separate in provenance; matching a spelling does not validate all its senses.
Run after each appended batch; --baseline verifies every original record/audio.
"""
import argparse
from collections import Counter
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.hsk_validate import hsk_segment, load_levels


LEGACY_BASELINE = "data/baselines/v1.2.1.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def audit(root=ROOT, baseline=None, require_audio=False):
    raw_path = root / "data/standards/gf0025-2021-7-9.txt"
    source = json.loads(raw_path.with_suffix(".source.json").read_text(encoding="utf-8"))
    rows = raw_path.read_text(encoding="utf-8").splitlines()
    target = set(rows)
    issues = []
    if digest(raw_path) != source["sha256"]:
        issues.append("Vocabulary snapshot SHA256 mismatch")
    if len(rows) != source["rows"] or len(target) != source["distinct_spellings"]:
        issues.append("Vocabulary snapshot counts mismatch")
    verification = json.loads(raw_path.with_suffix('.verification.json').read_text(encoding='utf-8'))
    word_forms_verified = (verification['transcription_sha256'] == digest(raw_path)
                           and verification['official_pdf_sha256'] == source['official_pdf']['sha256']
                           and verification['rows_checked'] == len(rows)
                           and verification['ocr_agreement_rows'] + verification['visually_reconciled_rows'] == len(rows)
                           and verification['unresolved_word_form_differences'] == 0)
    if not word_forms_verified:
        issues.append('Official word-form verification is stale or incomplete')
    records = json.loads((root / "dist/sentences.json").read_text(encoding="utf-8"))
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        issues.append("Duplicate record IDs")
    advanced = [r for r in records if r["hsk_level"] == 7]
    authored = yaml.safe_load((root / "data/sentences/hsk7.yaml").read_text(encoding="utf-8"))["sentences"]
    if len(advanced) != len(authored):
        issues.append("Advanced source/build record counts differ")
    word_level, _ = load_levels(maxlvl=6)
    if not word_level:
        raise ValueError("Download the 1-6 wordlists before auditing")
    word_level.update({w: 7 for w in target if w not in word_level})
    maxlen = max(map(len, word_level))
    high_used, incidental, intentional = set(), set(), set()
    unlisted, missing_audio, target_token_gaps, unlisted_tokens = {}, [], {}, {}
    duplicate_texts = Counter(r["chinese"] for r in records)
    for idx, r in enumerate(advanced, 1):
        sid = f"hsk7-{idx:04d}"
        if r["id"] != sid:
            issues.append(f"Advanced ID/order mismatch: {r['id']} != {sid}")
        if idx > len(authored):
            continue
        s = authored[idx - 1]
        if r["chinese"] != s["chinese"] or r["translation"]["en"] != s["en"]:
            issues.append(f"Source/build text differs: {sid}")
        if not r["translation"]["en"].strip() or not re.search('[A-Za-z]', r["translation"]["en"]):
            issues.append(f"Missing English translation: {sid}")
        if duplicate_texts[r["chinese"]] != 1:
            issues.append(f"Duplicate Chinese sentence: {sid}")
        if not s.get("targets"):
            issues.append(f"No intentional advanced vocabulary: {sid}")
        for w in s.get("targets", []):
            if w not in target or w not in r["chinese"]:
                issues.append(f"Invalid intentional target: {sid}: {w}")
            else:
                intentional.add(w)
        tokens = r["tokens"]
        text_tokens = [t["word"] for t in tokens]
        outside = sorted({w for w in text_tokens if w not in word_level})
        if outside:
            unlisted_tokens[sid] = outside
        if ''.join(re.findall('[一-鿿]', ''.join(text_tokens))) != ''.join(re.findall('[一-鿿]', r['chinese'])):
            issues.append(f"Token text does not reconstruct sentence: {sid}")
        for t in tokens:
            if not t["pinyin"] or not t["gloss_en"]:
                issues.append(f"Missing token pinyin/gloss: {sid}: {t['word']}")
        if r["pinyin"] != " ".join(t["pinyin"] for t in tokens):
            issues.append(f"Sentence/token pinyin mismatch: {sid}")
        if any(w not in text_tokens for w in s.get("targets", [])):
            target_token_gaps[sid] = [w for w in s["targets"] if w not in text_tokens]
        words = hsk_segment(r["chinese"], word_level, 7, maxlen=maxlen)
        high_used.update(set(words) & target)
        unknown = sorted({w for w in words if w not in word_level and re.search('[一-鿿]', w)})
        if unknown:
            unlisted[sid] = unknown
        for speed, suffix in (("normal", ""), ("slow", "_slow")):
            expected = f"audio/{sid}{suffix}.mp3"
            if r["audio"][speed] != expected:
                issues.append(f"Unexpected audio path: {sid} {speed}")
            p = root / "dist" / expected
            if not p.is_file() or p.stat().st_size == 0:
                missing_audio.append(expected)
    for r in records:
        if r["hsk_level"] != 7:
            incidental.update(set(hsk_segment(r["chinese"], word_level, 7, maxlen=maxlen)) & target)
    # A portable release fingerprint is checked even when the detailed local
    # per-file snapshot is unavailable on a later machine.
    # Each baseline = the previous release plus the pinyin-only amendments it lists.
    released = json.loads((root / LEGACY_BASELINE).read_text(encoding="utf-8"))
    legacy = [r for r in records if r["hsk_level"] <= 6]
    legacy_hash = sha256(json.dumps(legacy, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    original_ok = len(legacy) == released["records"] and legacy_hash == released["legacy_records_sha256"]
    audio_hashes = {}
    for r in legacy:
        for name in r["audio"].values():
            path = root / "dist" / name
            if path.is_file():
                audio_hashes[name] = digest(path)
    audio_tree = ''.join(f'{name}\0{value}\n' for name, value in sorted(audio_hashes.items())).encode("utf-8")
    original_ok = original_ok and len(audio_hashes) == released["audio_files"] and sha256(audio_tree).hexdigest() == released["audio_tree_sha256"]
    for name, value in released["reference"].items():
        original_ok = original_ok and (root / name).is_file() and digest(root / name) == value
    if not original_ok:
        issues.append(f"Released {released['release']} legacy records, audio or reference fingerprint changed")
    if baseline:
        baseline = Path(baseline)
        manifest = json.loads((baseline / "manifest.json").read_text(encoding="utf-8"))
        old = json.loads((baseline / "sentences.json").read_text(encoding="utf-8"))
        current = {r["id"]: r for r in records}
        violations = [r["id"] for r in old if current.get(r["id"]) != r]
        violations += [name for name, value in manifest["audio"].items()
                       if not (root / "dist" / name).is_file() or digest(root / "dist" / name) != value]
        violations += [name for name, value in manifest["reference"].items()
                       if not (root / name).is_file() or digest(root / name) != value]
        original_ok = original_ok and not violations
        issues.extend(f"Baseline changed: {name}" for name in violations)
    if require_audio and missing_audio:
        issues.append(f"Missing {len(missing_audio)} advanced audio files")
    packages = {}
    for name in ("pypinyin", "jieba", "opencc", "PyYAML"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "standard": "GF0025-2021", "band": "7-9", "storage_level": 7,
        "source": source, "records": len(records), "advanced_records": len(advanced),
        "text_packages": packages,
        "text_resource_sha256": {str(p.relative_to(root)).replace('\\', '/'): digest(p)
                                 for p in [root / "data/cedict/cedict.txt", *sorted((root / "data/hsk_wordlist").glob("new_*.json"))]
                                 if p.is_file()},
        "source_rows": len(rows), "distinct_target_spellings": len(target),
        "repeated_rows": {w: n for w, n in Counter(rows).items() if n > 1},
        "coverage_method": "level-aware segmentation against levels 1-6 plus the pinned 2021 advanced transcription; distinct spellings only",
        "advanced_spelling_coverage": {"covered": len(high_used), "total": len(target),
                                       "fraction": round(len(high_used) / len(target), 6)},
        "intentional_target_spellings": len(intentional),
        "incidental_spellings_in_legacy_records": len(incidental),
        "all_records_spelling_coverage": len(high_used | incidental),
        "missing_spellings": sorted(target - high_used),
        "unlisted_han_by_sentence": unlisted,
        "output_tokens_not_in_wordlists": unlisted_tokens,
        "intentional_targets_split_in_output": target_token_gaps,
        "advanced_audio_present": len(advanced) * 2 - len(missing_audio),
        "missing_audio": missing_audio, "legacy_baseline_unchanged": original_ok,
        "issues": issues,
        "status": "in_progress",
        "review_status": {"official_transcription": "All 5636 ordered word forms reconciled against the official scan; readings, qualifiers and senses remain separate checks",
                          "unlisted_vocabulary": "manual lexical review pending; no zero-OOV claim",
                          "grammar": "148-point coverage audited by scripts/audit_advanced_grammar.py (docs/advanced-grammar-coverage.md): 144 covered with >=2 candidate examples each (059/085/088/128 judged manually); 145-148 are sentence-group points that single-sentence records cannot show. Rule matches are candidates, not grammatical verification; records carry no per-sentence grammar IDs",
                          "listening": "ASR-screened per batch with seed retries; sentences still flagged after retries were listened to by the maintainer. Full listening review pending"},
        "limitations": ["Spelling coverage is not reading, sense, grammar or official sentence-grade validation.",
                         "Legacy incidental vocabulary does not count as newly authored advanced sentences.",
                         "Every listed spelling has at least one sentence; listening review of all audio and lexical review of unlisted vocabulary remain separate checks."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    info = audit(baseline=args.baseline, require_audio=args.require_audio)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in info.items() if k in {
        "advanced_records", "advanced_spelling_coverage", "intentional_target_spellings",
        "incidental_spellings_in_legacy_records", "advanced_audio_present", "legacy_baseline_unchanged", "issues"}}, ensure_ascii=False, indent=2))
    if info["issues"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
