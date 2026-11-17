"""Append an explicitly reviewed authoring batch, with stable sequential IDs."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOPICS = set('greetings identity family numbers time daily_actions school_work location transport shopping food weather_state questions objects_misc health_body sports_leisure feelings nature society economy science culture'.split())


def atomic_text(path, text):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.stem, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def validate_batch(draft, assignment, existing):
    expected = {t['word'] for t in assignment['targets']}
    official = set((ROOT / 'data/standards/gf0025-2021-7-9.txt').read_text(encoding='utf-8').splitlines())
    errors, seen = [], {re.sub('[^一-鿿]', '', s['chinese']) for s in existing}
    if draft.get('batch') != assignment['batch']:
        errors.append('Batch/assignment ID mismatch')
    used = set()
    for i, s in enumerate(draft.get('sentences', []), 1):
        prefix = f"{draft.get('batch')}:{i}"
        zh, en = s.get('chinese', ''), s.get('en', '')
        key = re.sub('[^一-鿿]', '', zh)
        if not 10 <= len(key) <= 50 or re.search('[A-Za-z0-9]', zh) or not zh.endswith(('。', '！', '？')):
            errors.append(f'{prefix}: Chinese format/length')
        if key in seen:
            errors.append(f'{prefix}: duplicate Chinese')
        seen.add(key)
        if not re.search('[A-Za-z]', en) or re.search('[一-鿿]', en):
            errors.append(f'{prefix}: invalid English')
        if s.get('topic') not in TOPICS:
            errors.append(f'{prefix}: unknown topic')
        if not s.get('targets'):
            errors.append(f'{prefix}: no target words')
        for w in s.get('targets', []):
            used.add(w)
            if w not in official or w not in expected or w not in zh:
                errors.append(f'{prefix}: invalid/unassigned target {w}')
            if not s.get('token_pinyin', {}).get(w) or not s.get('gloss', {}).get(w):
                errors.append(f'{prefix}: target reading/gloss missing for {w}')
            elif re.search(r'[0-9]', s['token_pinyin'][w]):
                errors.append(f'{prefix}: target pinyin must use tone marks, not digits: {w}')
        if s.get('grammar') != []:
            errors.append(f'{prefix}: grammar IDs require a separate registry review')
    missing = expected - used
    if missing:
        errors.append('Uncovered assigned words: ' + ' '.join(sorted(missing)))
    if draft.get('exceptions'):
        errors.append('Unresolved lexical exceptions require explicit resolution')
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--draft', type=Path, required=True)
    ap.add_argument('--assignment', type=Path, required=True)
    ap.add_argument('--review', type=Path, required=True)
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()
    content = args.draft.read_bytes()
    draft, assignment = json.loads(content), json.loads(args.assignment.read_text(encoding='utf-8'))
    review = json.loads(args.review.read_text(encoding='utf-8'))
    if review.get('draft_sha256') != sha256(content).hexdigest() or review.get('status') != 'approved_for_build':
        raise SystemExit('Missing or stale review approval')
    source = ROOT / 'data/sentences/hsk7.yaml'
    existing_text = source.read_text(encoding='utf-8')
    existing = yaml.safe_load(existing_text)['sentences']
    registry = ROOT / 'data/advanced_batches.json'
    batches = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else []
    if any(b['batch'] == draft['batch'] for b in batches):
        raise SystemExit('Batch already imported; IDs must not be assigned twice')
    canonical_path = ROOT / 'dist/sentences.json'
    canonical = json.loads(canonical_path.read_text(encoding='utf-8')) if canonical_path.exists() else []
    errors = validate_batch(draft, assignment, existing + canonical)
    if errors:
        raise SystemExit('\n'.join(errors))
    first, last = len(existing) + 1, len(existing) + len(draft['sentences'])
    info = {'batch': draft['batch'], 'first_id': f'hsk7-{first:04d}', 'last_id': f'hsk7-{last:04d}',
            'sentences': len(draft['sentences']), 'assigned_targets': len(assignment['targets']),
            'draft_sha256': sha256(content).hexdigest(), 'reviewer': review.get('reviewer'),
            'review_notes': review.get('notes', []), 'audio_method': 'native PCM -> atempo=0.8',
            'quality_status': 'assistant text review; listening review remains pending'}
    if assignment.get('parent_batch'):
        info['parent_batch'] = assignment['parent_batch']
    if args.write:
        added = ['\n  # —— ' + draft['batch'] + ' ——']
        for s in draft['sentences']:
            added.append('  - ' + yaml.safe_dump(s, allow_unicode=True, default_flow_style=True,
                                                width=10000, sort_keys=False).strip())
        atomic_text(source, existing_text.rstrip() + '\n' + '\n'.join(added) + '\n')
        atomic_text(registry, json.dumps(batches + [info], ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
