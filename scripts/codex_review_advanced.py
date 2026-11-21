"""Independent per-sentence review of an advanced draft via the local Codex CLI.

Runs `codex exec` (ChatGPT plan, default model gpt-6.1-sol, high effort) on
checkpointed chunks. Each call runs in an empty temp directory with a read-only
sandbox and --ephemeral, so the reviewer cannot read or change the repository.
Replacements may only change chinese/en/topic/target pinyin/target gloss; the
target word is fixed. Output is a reviewed draft plus a review record. This
never writes an approved_for_build file, imports data or generates audio:
assistant acceptance stays a separate, explicit step.

Dry run (no calls):  python scripts/codex_review_advanced.py --draft D --assignment A
Paid run:            ... --run
Gateway fallback:    ... --run --backend gateway --max-spend-usd 2
  (same prompt and model through AI Gateway, with its own ledger under
  .local/advanced-bulk/gateway/review-<batch>; chunks already reviewed by the
  Codex backend are reused, never sent again)
"""
from decimal import Decimal
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_advanced_batch import TOPICS, atomic_text, validate_batch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

PROMPT = """你是独立的中文高级教材审校者。逐句审核另一模型的原创例句，不能敷衍放行。
不要使用任何工具，不要读写文件或运行命令，只根据下面给出的 JSON 作答。
检查：目标词确实作为该词或正确词素使用，词性搭配自然，句意具体可信，英文准确，带调拼音读音/轻声正确且与语境一致，英文词义只解释本句义项。
单字目标不能躲在不相关的复合词里，例如用学习冒充习。可分词素需有词表本义的自然派生语境。
不要仅因词语高级、话题负面或出现常见词表外复合词就改句。不要提出纯风格偏好。
不改变目标词，不新增目标，不改变句子数量和顺序。中文十至五十汉字，无拉丁字母或数字，以。！？结尾。
拼音用声调符号，音节间空格，轻声不标调，不写数字。topic 必须从 allowed_topics 选取。
必须逐项返回每个从零开始的 index，不能遗漏或重复。
合格句：status=accept，issues=[]，replacement=null。
需修正：status=revise，issues 写明具体问题；能可靠修正时给出 replacement
（chinese、en、topic、target_pinyin、target_gloss；改中文须同步改英文、读音和词义），
无法可靠修正时 replacement=null。独立阅读每一句后再提交。

"""

REPLACEMENT = {
    "type": "object", "additionalProperties": False,
    "required": ["chinese", "en", "topic", "target_pinyin", "target_gloss"],
    "properties": {"chinese": {"type": "string"}, "en": {"type": "string"},
                   "topic": {"type": "string", "enum": sorted(TOPICS)},
                   "target_pinyin": {"type": "string"}, "target_gloss": {"type": "string"}},
}
SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["reviews"],
    "properties": {"reviews": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["index", "status", "issues", "replacement"],
        "properties": {"index": {"type": "integer"},
                       "status": {"type": "string", "enum": ["accept", "revise"]},
                       "issues": {"type": "array", "items": {"type": "string"}},
                       "replacement": {"anyOf": [REPLACEMENT, {"type": "null"}]}}}}},
}


def find_codex():
    if os.environ.get("CODEX_EXE"):
        return os.environ["CODEX_EXE"]
    # WindowsApps cannot be listed by normal users, so ask AppX for the install path.
    proc = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                           "(Get-AppxPackage -Name OpenAI.Codex | Sort-Object Version | Select-Object -Last 1).InstallLocation"],
                          capture_output=True, text=True)
    exe = Path(proc.stdout.strip()) / "app" / "resources" / "codex.exe"
    if not proc.stdout.strip() or not exe.exists():
        raise SystemExit("codex.exe not found; set CODEX_EXE")
    return str(exe)


def review_chunk(codex, model, effort, sentences, lexical, timeout):
    content = json.dumps({"allowed_topics": sorted(TOPICS), "lexical_reference": lexical,
                          "sentences": sentences}, ensure_ascii=False)
    with tempfile.TemporaryDirectory(prefix="codex-review-") as tmp:
        schema, out = Path(tmp) / "schema.json", Path(tmp) / "out.json"
        schema.write_text(json.dumps(SCHEMA), encoding="utf-8")
        work = Path(tmp) / "empty"
        work.mkdir()
        cmd = [codex, "exec", "-m", model, "-c", f"model_reasoning_effort={effort}",
               "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "-C", str(work),
               "--output-schema", str(schema), "-o", str(out), "-"]
        proc = subprocess.run(cmd, input=PROMPT + content, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
        if proc.returncode != 0 or not out.exists():
            raise RuntimeError(f"codex exec failed ({proc.returncode}): {proc.stderr[-800:] or proc.stdout[-800:]}")
        tokens = None
        lines = (proc.stdout + "\n" + proc.stderr).splitlines()
        for i, line in enumerate(lines):
            if line.strip() == "tokens used" and i + 1 < len(lines):
                tokens = int(lines[i + 1].replace(",", "").strip() or 0)
        return json.loads(out.read_text(encoding="utf-8")), tokens


GATEWAY_FORMAT = """
只输出 JSON 对象 {"reviews":[{"index":0,"status":"accept","issues":[],"replacement":null}]}；
replacement 为 null 或 {"chinese":"","en":"","topic":"","target_pinyin":"","target_gloss":""}。
"""


def workflow_hash(backend, model, effort):
    extra = GATEWAY_FORMAT if backend == "gateway" else ""
    tag = "" if backend == "codex" else "gateway:"
    return sha256((tag + model + effort + PROMPT + extra + json.dumps(SCHEMA)).encode()).hexdigest()


def gateway_reviewer(model, effort, max_spend, state_dir):
    from gateway_advanced import Gateway
    gw = Gateway(state_dir, max_spend)
    model_id = f"openai/{model}"
    if model_id not in gw.catalog:
        raise SystemExit(f"Model absent from Gateway catalog: {model_id}")

    def review(sentences, lexical, name):
        content = json.dumps({"allowed_topics": sorted(TOPICS), "lexical_reference": lexical,
                              "sentences": sentences}, ensure_ascii=False)
        result, _ = gw.complete(name, model_id, PROMPT + GATEWAY_FORMAT, content, 16000, {"effort": effort})
        return result, None
    return review, gw


def apply_reviews(chunk, reviews):
    if sorted(r["index"] for r in reviews) != list(range(len(chunk))):
        raise ValueError("Incomplete or duplicated review indices")
    out, revised, unresolved = [dict(s) for s in chunk], [], []
    for r in reviews:
        if r["status"] == "accept":
            if r["issues"] or r["replacement"] is not None:
                raise ValueError(f"Inconsistent accept at index {r['index']}")
            continue
        if not r["issues"]:
            raise ValueError(f"Revise without issues at index {r['index']}")
        if r["replacement"] is None:
            unresolved.append(r)
            continue
        s, rep = out[r["index"]], r["replacement"]
        (word,) = s["targets"]
        out[r["index"]] = {"chinese": rep["chinese"], "en": rep["en"], "topic": rep["topic"],
                           "targets": [word], "token_pinyin": {word: rep["target_pinyin"]},
                           "gloss": {word: rep["target_gloss"]}, "grammar": []}
        revised.append(r["index"])
    return out, revised, unresolved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draft", type=Path, required=True)
    ap.add_argument("--assignment", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--chunk-size", type=int, default=20)
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--backend", choices=["codex", "gateway"], default="codex")
    ap.add_argument("--max-spend-usd", type=Decimal)
    args = ap.parse_args()
    if not 1 <= args.chunk_size <= 25:
        ap.error("chunk-size 1..25")
    if args.backend == "gateway" and args.run and (args.max_spend_usd is None or args.max_spend_usd <= 0):
        ap.error("--backend gateway requires an explicit positive --max-spend-usd")

    raw = args.draft.read_bytes()
    draft = json.loads(raw)
    assignment = json.loads(args.assignment.read_text(encoding="utf-8"))
    targets = assignment["targets"]
    sentences = draft["sentences"]
    if [s["targets"] for s in sentences] != [[t["word"]] for t in targets]:
        raise SystemExit("Draft targets do not match the assignment order (one target per sentence)")
    out_dir = args.out_dir or ROOT / ".local/advanced-bulk/codex-review" / draft["batch"]
    chunks = [range(i, min(i + args.chunk_size, len(sentences))) for i in range(0, len(sentences), args.chunk_size)]
    print(json.dumps({"batch": draft["batch"], "sentences": len(sentences), "chunks": len(chunks),
                      "model": args.model, "effort": args.effort, "backend": args.backend, "calls": args.run}, ensure_ascii=False), flush=True)
    if not args.run:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    draft_hash = sha256(raw).hexdigest()
    workflow = workflow_hash(args.backend, args.model, args.effort)
    reusable = {workflow_hash("codex", args.model, args.effort): "codex", workflow: args.backend}
    gw = None
    if args.backend == "codex":
        codex = find_codex()
        reviewer = lambda chunk, lexical, name: review_chunk(codex, args.model, args.effort, chunk, lexical, args.timeout)  # noqa: E731
    else:
        reviewer, gw = gateway_reviewer(args.model, args.effort, args.max_spend_usd,
                                        ROOT / ".local/advanced-bulk/gateway" / f"review-{draft['batch']}")
    chunk_backends = []

    reviewed, revised_all, unresolved_all, total_tokens = [], [], [], 0
    for n, ix in enumerate(chunks):
        chunk = [sentences[i] for i in ix]
        lexical = [{"word": targets[i]["word"], "readings_and_glosses": targets[i]["readings_and_glosses"]} for i in ix]
        chunk_hash = sha256(json.dumps(chunk, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        ckpt = out_dir / f"{draft['batch']}-{n:02d}.review.json"
        if ckpt.exists():
            cached = json.loads(ckpt.read_text(encoding="utf-8"))
            if cached["chunk_sha256"] != chunk_hash or cached["workflow_sha256"] not in reusable:
                raise SystemExit(f"{ckpt.name}: checkpoint does not match draft/workflow; inspect before reuse")
            result, tokens = cached["result"], cached.get("tokens_used")
            chunk_backends.append(reusable[cached["workflow_sha256"]])
            print(f"{ckpt.stem}: cached", flush=True)
        else:
            t0 = time.time()
            result, tokens = reviewer(chunk, lexical, ckpt.stem)
            chunk_backends.append(args.backend)
            atomic_text(ckpt, json.dumps({"chunk_sha256": chunk_hash, "workflow_sha256": workflow, "backend": args.backend,
                                          "first_index": ix.start, "tokens_used": tokens, "result": result},
                                         ensure_ascii=False, indent=2) + "\n")
            spent = f", spent ${gw.spent}" if gw else ""
            print(f"{ckpt.stem}: {len(chunk)} reviewed in {time.time() - t0:.0f}s, tokens {tokens}{spent}", flush=True)
        fixed, revised, unresolved = apply_reviews(chunk, result["reviews"])
        reviewed += fixed
        revised_all += [ix.start + i for i in revised]
        unresolved_all += [{**r, "index": ix.start + r["index"]} for r in unresolved]
        total_tokens += tokens or 0

    new_draft = {"batch": draft["batch"], "exceptions": [], "sentences": reviewed}
    canonical = json.loads((ROOT / "dist/sentences.json").read_text(encoding="utf-8"))
    errors = validate_batch(new_draft, assignment, canonical)
    record = {"batch": draft["batch"], "source_draft_sha256": draft_hash,
              "review_model": f"openai/{args.model}, effort {args.effort}, via "
                              + " + ".join(sorted({"Codex CLI (ChatGPT plan)" if b == "codex" else "AI Gateway"
                                                   for b in chunk_backends})),
              "chunk_backends": chunk_backends,
              "gateway_spent_usd": str(gw.spent) if gw else None,
              "sentences": len(reviewed), "revised_indices": revised_all, "unresolved": unresolved_all,
              "validation_errors": errors, "tokens_used": total_tokens,
              "status": "independent_model_review_complete; assistant acceptance pending"}
    atomic_text(out_dir / f"{draft['batch']}.reviewed-draft.json",
                json.dumps(new_draft, ensure_ascii=False, indent=2) + "\n")
    atomic_text(out_dir / f"{draft['batch']}.codex-review.json",
                json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(f"revised {len(revised_all)}, unresolved {len(unresolved_all)}, validation errors {len(errors)}, "
          f"tokens {total_tokens}", flush=True)
    if unresolved_all or errors:
        sys.exit(2)


if __name__ == "__main__":
    main()
