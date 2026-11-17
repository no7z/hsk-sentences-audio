"""Checkpointed advanced-sentence authoring through an explicitly configured Gateway.

Paid requests require --run and --max-spend-usd. This never imports drafts,
changes credentials, purchases credits, or generates audio. Runtime artifacts
and the ledger stay in ignored .local/. Independent model review is a screening
step; it does not establish human listening or full standard compliance.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request

from import_advanced_batch import TOPICS, atomic_text, validate_batch

ROOT = Path(__file__).resolve().parents[1]
API = 'https://ai-gateway.vercel.sh/v1'
AUTHOR = 'anthropic/claude-fable-5.2'
REVIEWER = 'openai/gpt-6-astra'
SYSTEM = """你是严谨的对外汉语教材编写者。根据用户提供的 GF0025-2021 高等词表项目写原创例句，不编造词表项目。
每个指定词写一句，按输入顺序，目标词必须原样连续出现且用作独立词/正确词素，不以其他长词中碰巧包含该字来冒充覆盖。
句子自然具体，单句或有逻辑的复句，约十五至三十五汉字，允许十至五十汉字；适合成人学习者。
情境要使目标义项清楚，避免空泛释义模板、生硬搭配、流水账、牵强高级词堆砌。
对单字、多音词、语气词尤其谨慎。单字目标必须符合其常用词性、读音和搭配。
提供忠实自然的英文译文。中文不含阿拉伯数字或拉丁字母，以。！？结尾。
拼音使用带声调符号的词典原调，音节间空格，轻声不标调，不写拼音数字。英文词义只解释此句中的目标词义。
词典参考仅供辨读，义项可能不全或译释不准，不能机械照抄。需根据语境自主确定正确、常用的词义与英文。
若用户指定读音或义项，必须遵守；普通造句以当代自然用法为主。英文必须是语法完整、惯用且忠实的句子。
不要把分级错误当作词汇扩充，不借用新版考试分级。不要输出语法编号。
只输出 JSON 对象 {"sentences":[{"chinese":"...","en":"...","topic":"...","targets":["输入词"],"token_pinyin":{"输入词":"..."},"gloss":{"输入词":"..."},"grammar":[]}]}。
每句只标注当前指定的一个目标词，不能合并或遗漏。topic 必须从给定允许列表选取。"""
REVIEW_SYSTEM = """你是独立的中文高级教材审校者。逐句审核另一模型的原创例句，不能敷衍放行。
检查：目标词确实作为该词或正确词素使用，词性搭配自然，句意具体可信，英文准确，带调拼音读音/轻声正确且与语境一致，英文词义只解释本句义项。
单字目标不能躲在不相关的复合词里，例如用学习冒充习。可分词素需有词表本义的自然派生语境。
不要仅因词语高级、话题负面或出现常见词表外复合词就改句。不要提出纯风格偏好。
不改变目标词，不新增目标，不改变句子数量和顺序。中文十至五十汉字，无拉丁字母或数字，以。！？结尾。
返回 JSON {"reviews":[{"index":0,"status":"accept或revise","issues":["具体问题"],"replacement":完整修正后的句子对象或null}]}。
必须逐项返回每个从零开始的索引，不能遗漏或重复。合格句 status:accept,issues:[],replacement:null。
需修正句 status:revise，issues 说明具体问题。无法可靠修正时 replacement:null，不能勉强通过。
修正对象完整保留 chinese,en,topic,targets,token_pinyin,gloss,grammar 字段。
若修改中文需同步修改英文及相关读音词义。grammar 恒为空列表。独立阅读每一句后再提交。"""


def read_key():
    value = os.environ.get('AI_GATEWAY_API_KEY', '')
    if not value:
        path = ROOT / '.env.local'
        for raw in path.read_text(encoding='utf-8-sig').splitlines():
            line = raw.strip().removeprefix('export ').lstrip()
            if line.startswith('AI_GATEWAY_API_KEY='):
                value = line.split('=', 1)[1].strip()
                if value[:1] in ('"', "'"):
                    quote = value[0]
                    end = value.find(quote, 1)
                    if end < 1:
                        raise ValueError('Unclosed key quote')
                    value = value[1:end]
                else:
                    value = value.split(' #', 1)[0].strip()
    if not value or any(c.isspace() for c in value):
        raise ValueError('Valid AI_GATEWAY_API_KEY required in environment or .env.local')
    return value


class Gateway:
    def __init__(self, directory, max_spend):
        self.key = read_key()
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.ledger = directory / 'ledger.jsonl'
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.limit = Decimal(str(max_spend))
        self.reserved = Decimal(0)
        self.spent = Decimal(0)
        if self.ledger.exists():
            entries = [json.loads(s) for s in self.ledger.read_text(encoding='utf-8').splitlines()]
            starts = {e['request_id']: e for e in entries if e['event'] == 'start'}
            finishes = {e['request_id']: e for e in entries if e['event'] == 'finish'}
            # Unknown outcomes retain their worst-case reservation after interruption.
            for rid, entry in starts.items():
                self.spent += Decimal(str(finishes.get(rid, {}).get('cost_usd', entry['reserved_usd'])))
        self.models = self.get('/models', auth=False)
        atomic_text(directory / 'models.json', json.dumps(self.models, ensure_ascii=False, indent=2) + '\n')
        self.catalog = {m['id']: m for m in self.models['data']}
        for model in (AUTHOR, REVIEWER):
            if model not in self.catalog:
                raise ValueError(f'Model absent from current catalog: {model}')

    def get(self, path, auth=True):
        headers = {'Authorization': 'Bearer ' + self.key} if auth else {}
        with urllib.request.urlopen(urllib.request.Request(API + path, headers=headers), timeout=30) as res:
            return json.load(res)

    def log(self, event):
        with self.ledger.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + '\n')
            handle.flush()
            os.fsync(handle.fileno())

    def complete(self, name, model, system, content, max_tokens, reasoning=None):
        if getattr(self, 'stop_event', None) is not None and self.stop_event.is_set():
            raise RuntimeError('Another chunk failed; paid work is halted until inspected')
        price = self.catalog[model]['pricing']
        inp, out = Decimal(price['input']), Decimal(price['output'])
        # UTF-8 bytes are a conservative token upper bound for these text prompts.
        upper_input = len((system + content).encode('utf-8')) + 512
        reserve = inp * upper_input + out * max_tokens
        rid = f'{name}-{time.time_ns()}'
        with self.lock:
            if getattr(self, 'stop_event', None) is not None and self.stop_event.is_set():
                raise RuntimeError('Another chunk failed; paid work is halted until inspected')
            balance = Decimal(str(self.get('/credits')['balance']))
            if self.spent + self.reserved + reserve > self.limit or balance - self.reserved - reserve < Decimal('0.15'):
                raise RuntimeError('Local spending cap or remaining credit reserve reached')
            self.reserved += reserve
            self.log({'event': 'start', 'request_id': rid, 'name': name, 'model': model,
                      'reserved_usd': str(reserve), 'prompt_sha256': sha256((system + content).encode()).hexdigest()})
        payload = {'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': content}],
                   'max_tokens': max_tokens,
                   'response_format': {'type': 'json_object'}, 'stream': False}
        if reasoning:
            payload['reasoning'] = reasoning
        req = urllib.request.Request(API + '/chat/completions', data=json.dumps(payload, ensure_ascii=False).encode(),
                                     headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=240) as res:
                result = json.load(res)
            # Responses contain generated content and usage, never request headers.
            atomic_text(self.directory / f'{rid}.json', json.dumps(result, ensure_ascii=False, indent=2) + '\n')
            usage = result['usage']
            estimated = inp * usage['prompt_tokens'] + out * usage['completion_tokens']
            cost = Decimal(str(usage.get('cost', estimated)))
            if cost < 0:
                raise ValueError('Invalid generation cost')
            with self.lock:
                self.spent += cost
                self.reserved -= reserve
                self.log({'event': 'finish', 'request_id': rid, 'generation_id': result['id'], 'model': result.get('model'),
                          'cost_usd': str(cost), 'usage': usage, 'finish_reason': result['choices'][0]['finish_reason']})
            if result['choices'][0]['finish_reason'] != 'stop':
                raise ValueError(f'Incomplete model output for {name}')
            text = result['choices'][0]['message']['content'].strip()
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
            return json.loads(text), result['id']
        except Exception:
            # Failed/unknown outcomes keep their reservation; no invisible paid retry.
            with self.lock:
                self.log({'event': 'error', 'request_id': rid, 'name': name, 'note': 'No automatic retry; inspect safe response artifact or HTTP status.'})
            raise


def chunk_work(gateway, assignment, targets, index, output, existing):
    path = output / f'{assignment["batch"]}-{index:02d}.json'
    target_hash = sha256(json.dumps(targets, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    workflow_hash = sha256((AUTHOR + REVIEWER + SYSTEM + REVIEW_SYSTEM).encode()).hexdigest()
    if path.exists():
        cached = json.loads(path.read_text(encoding='utf-8'))
        if cached['target_sha256'] != target_hash or cached.get('workflow_sha256') != workflow_hash:
            raise ValueError('Checkpoint assignment/model/prompt changed; explicitly review migration before reuse')
        print(f'{path.stem}: cached', flush=True)
        return cached
    compact = [{'word': t['word'], 'readings_and_glosses': t['readings_and_glosses']} for t in targets]
    content = json.dumps({'allowed_topics': sorted(TOPICS), 'targets': compact}, ensure_ascii=False)
    author_checkpoint = path.with_suffix('.authored.json')
    if author_checkpoint.exists():
        checkpoint = json.loads(author_checkpoint.read_text(encoding='utf-8'))
        if checkpoint.get('target_sha256') != target_hash or checkpoint.get('workflow_sha256') != workflow_hash:
            raise ValueError('Author checkpoint assignment/model/prompt changed')
        authored, author_id = checkpoint['result'], checkpoint['generation_id']
    else:
        authored, author_id = gateway.complete(path.stem + '-author', AUTHOR, SYSTEM, content, 10000, {'effort': 'high'})
        atomic_text(author_checkpoint, json.dumps({'target_sha256': target_hash, 'workflow_sha256': workflow_hash,
                    'result': authored, 'generation_id': author_id}, ensure_ascii=False, indent=2) + '\n')
    sub_assignment = {**assignment, 'targets': targets}
    draft = {'batch': assignment['batch'], 'exceptions': [], 'sentences': authored['sentences']}
    if len(draft['sentences']) != len(targets) or [s['targets'] for s in draft['sentences']] != [[t['word']] for t in targets]:
        raise ValueError('Author omitted/reordered/combined targets')
    errors = validate_batch(draft, sub_assignment, existing)
    if errors:
        atomic_text(path.with_suffix('.invalid.json'), json.dumps(draft, ensure_ascii=False, indent=2) + '\n')
        raise ValueError('\n'.join(errors))
    review_content = json.dumps({'allowed_topics': sorted(TOPICS), 'lexical_reference': compact, 'sentences': draft['sentences']}, ensure_ascii=False)
    reviewed, reviewer_id = gateway.complete(path.stem + '-review', REVIEWER, REVIEW_SYSTEM, review_content, 10000, {'effort': 'high'})
    atomic_text(path.with_suffix('.reviewed.json'), json.dumps({'result': reviewed, 'generation_id': reviewer_id}, ensure_ascii=False, indent=2) + '\n')
    reviews = reviewed.get('reviews', [])
    if sorted(r.get('index', -1) for r in reviews) != list(range(len(targets))):
        raise ValueError('Incomplete independent review')
    seen = set()
    for issue in reviews:
        ix = issue['index']
        if issue.get('status') == 'accept' and issue.get('issues') == [] and issue.get('replacement') is None:
            continue
        if issue.get('status') != 'revise':
            raise ValueError('Invalid review status')
        if type(ix) is not int or ix < 0 or ix >= len(targets) or ix in seen or not issue.get('issues') or not issue.get('replacement'):
            atomic_text(path.with_suffix('.unresolved.json'), json.dumps({'draft': draft, 'review': reviewed}, ensure_ascii=False, indent=2) + '\n')
            raise ValueError('Unresolved/invalid independent review')
        seen.add(ix)
        draft['sentences'][ix] = issue['replacement']
    if [s['targets'] for s in draft['sentences']] != [[t['word']] for t in targets]:
        raise ValueError('Reviewer altered targets')
    errors = validate_batch(draft, sub_assignment, existing)
    if errors:
        raise ValueError('\n'.join(errors))
    result = {'target_sha256': target_hash, 'workflow_sha256': workflow_hash, 'author_model': AUTHOR, 'review_model': REVIEWER,
              'author_generation': author_id, 'review_generation': reviewer_id,
              'sentences': draft['sentences'], 'review': reviewed,
              'status': 'independent_model_review_complete; assistant acceptance pending'}
    atomic_text(path, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'{path.stem}: {len(targets)} reviewed, {len(seen)} corrections; ledger USD {gateway.spent:.4f}', flush=True)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--batches', nargs='+', required=True)
    ap.add_argument('--chunk-size', type=int, default=20)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--pilot-limit', type=int)
    ap.add_argument('--max-spend-usd', type=Decimal)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if not 1 <= args.chunk_size <= 25 or not 1 <= args.workers <= 3:
        ap.error('chunk-size 1..25, workers 1..3')
    assignments = [json.loads((ROOT / f'.local/advanced-bulk/assignments/{b}.json').read_text(encoding='utf-8')) for b in args.batches]
    print(json.dumps({'batches': args.batches, 'targets': sum(len(a['targets']) for a in assignments),
                      'author': AUTHOR, 'reviewer': REVIEWER, 'paid_requests': args.run}, ensure_ascii=False), flush=True)
    if not args.run:
        return
    if args.max_spend_usd is None or args.max_spend_usd <= 0:
        ap.error('Explicit positive spend cap required for this run')
    state = ROOT / '.local/advanced-bulk/gateway'
    state.mkdir(parents=True, exist_ok=True)
    lockfile = state / 'run.lock'
    fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        gateway = Gateway(state / 'requests', args.max_spend_usd)
        existing = json.loads((ROOT / 'dist/sentences.json').read_text(encoding='utf-8'))
        output = state / 'chunks'; output.mkdir(exist_ok=True)
        def guarded_chunk(*work_args):
            if gateway.stop_event.is_set():
                raise RuntimeError('Batch halted after another chunk failed')
            try:
                return chunk_work(*work_args)
            except Exception:
                gateway.stop_event.set()
                raise
        for a in assignments:
            targets = a['targets'][:args.pilot_limit] if args.pilot_limit else a['targets']
            chunks = [targets[i:i+args.chunk_size] for i in range(0, len(targets), args.chunk_size)]
            results = {}
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                work = {pool.submit(guarded_chunk, gateway, a, chunk, i, output, existing): i for i, chunk in enumerate(chunks)}
                for future in as_completed(work):
                    results[work[future]] = future.result()
            draft = {'batch': a['batch'], 'exceptions': [], 'sentences': [s for i in sorted(results) for s in results[i]['sentences']]}
            # A reviewed prefix may already have been imported during a credit
            # handoff. Exempt only the exact registered parent-batch records;
            # changed text or unrelated duplicate records still fail validation.
            registered = json.loads((ROOT / 'data/advanced_batches.json').read_text(encoding='utf-8'))
            allowed = set()
            text_pairs = {(s['chinese'], s['en']) for s in draft['sentences']}
            for batch in registered:
                if batch.get('parent_batch') == a['batch']:
                    for record in existing:
                        if batch['first_id'] <= record['id'] <= batch['last_id']:
                            if (record['chinese'], record['translation']['en']) not in text_pairs:
                                raise ValueError('Previously imported parent-batch text changed')
                            allowed.add(record['id'])
            errors = validate_batch(draft, {**a, 'targets': targets}, [r for r in existing if r['id'] not in allowed])
            if errors:
                raise ValueError('\n'.join(errors))
            suffix = '.pilot' if args.pilot_limit else ''
            dest = ROOT / f'.local/advanced-bulk/drafts/{a["batch"]}{suffix}.json'
            atomic_text(dest, json.dumps(draft, ensure_ascii=False, indent=2) + '\n')
            print(f'{a["batch"]}: draft ready for assistant acceptance ({len(draft["sentences"])} sentences)', flush=True)
        print(f'Ledger total USD {gateway.spent:.6f}; remaining credit USD {gateway.get("/credits")["balance"]}', flush=True)
    finally:
        lockfile.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
