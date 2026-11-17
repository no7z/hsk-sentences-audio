"""Independently review complete compiled advanced annotations, without applying edits.

Requires explicit --run and a spend cap for paid calls. Review outputs stay in
ignored .local/ and require assistant acceptance before metadata is amended.
This complements target-word authoring review and never edits audio or text.
"""
import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

import yaml

from gateway_advanced import Gateway, REVIEWER, ROOT, atomic_text

SYSTEM = """你是中文教材的注音、分词和英汉词义终审编辑。审核的是完整构建结果，不只目标词。
逐句阅读中文、英文和全部 tokens。发现不正确的多音字、轻声、儿化、词性义项、量词或语法功能释义、非自然分词时，逐项指出并给出具体修正。
常见陷阱包括：长时间的长是cháng，教授名词是jiào shòu，都表示全部是dōu，缝衣服是féng，红着眼睛中的着是zhe。
词典可能把量词台译成古语“you”，把次译成second，把人名王译成king，把名词布译成announce，把地点的后译成empress；都需要结合本句审查。
不要只复述这些例子。检查每一个词，包括非目标词、语气词和专名。字典式释义可以含本句适用的多个近义词，但不能只有无关义项。
自然复合词不应仅为满足有限词表而拆成错误的字符义，如床单、牛肉面和附录。
拼音采用带调词典原调（不改一、不的语流变调），音节空格分隔；轻声不标调，儿化r并入前一音节。
中文和英文已经另行审校，本轮不自行改写；若发现确实需要改文，作为text_issue指出，不能靠改词义掩盖问题。
返回JSON {"reviews":[{"id":"原id","issues":[{"word":"现有token或需分词的连续片段","reason":"具体问题","pinyin":"建议的带调拼音，或空串","gloss_en":"建议英文词义，或空串","segmentation":["建议分词，若无需改变则空数组"]}],"text_issue":"若无需改文则空串"}]}。
必须覆盖每个输入id，不能遗漏或重复。合格句issues为空数组。只提出实质性问题，不做纯风格修改。"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--from-id', type=int, required=True)
    ap.add_argument('--to-id', type=int, required=True)
    ap.add_argument('--chunk-size', type=int, default=12)
    ap.add_argument('--max-spend-usd', type=Decimal)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if not 1 <= args.from_id <= args.to_id or not 1 <= args.chunk_size <= 20:
        ap.error('Positive ordered ID range and chunk size 1..20 required')
    data = json.loads((ROOT / 'dist/sentences.json').read_text(encoding='utf-8'))
    sources = yaml.safe_load((ROOT / 'data/sentences/hsk7.yaml').read_text(encoding='utf-8'))['sentences']
    records = [{'id': r['id'], 'chinese': r['chinese'], 'en': r['translation']['en'],
                'targets': sources[int(r['id'].split('-')[1]) - 1]['targets'], 'tokens': r['tokens']}
               for r in data if r['hsk_level'] == 7 and args.from_id <= int(r['id'].split('-')[1]) <= args.to_id]
    if len(records) != args.to_id - args.from_id + 1:
        raise ValueError('Requested IDs missing')
    print(json.dumps({'records': len(records), 'reviewer': REVIEWER, 'paid_requests': args.run}), flush=True)
    if not args.run:
        return
    if args.max_spend_usd is None or args.max_spend_usd <= 0:
        ap.error('Explicit positive spend cap required')
    directory = ROOT / '.local/advanced-bulk/metadata-review'
    directory.mkdir(parents=True, exist_ok=True)
    gateway = Gateway(directory / 'requests', args.max_spend_usd)
    for i in range(0, len(records), args.chunk_size):
        chunk = records[i:i + args.chunk_size]
        content = json.dumps(chunk, ensure_ascii=False)
        fingerprint = sha256((SYSTEM + REVIEWER + content).encode()).hexdigest()
        dest = directory / f'{chunk[0]["id"]}-{chunk[-1]["id"]}-{fingerprint[:12]}.json'
        if dest.exists():
            print(f'{dest.stem}: cached', flush=True)
            continue
        result, generation = gateway.complete(dest.stem, REVIEWER, SYSTEM, content, 16000, {'effort': 'high'})
        if sorted(r.get('id', '') for r in result.get('reviews', [])) != sorted(r['id'] for r in chunk):
            raise ValueError('Incomplete compiled annotation review')
        output = {'status': 'review_complete; assistant acceptance and application pending',
                  'model': REVIEWER, 'generation_id': generation, 'input_sha256': fingerprint,
                  'input': chunk, 'result': result}
        atomic_text(dest, json.dumps(output, ensure_ascii=False, indent=2) + '\n')
        print(f'{dest.stem}: {sum(len(r["issues"]) for r in result["reviews"])} issues', flush=True)


if __name__ == '__main__':
    main()
