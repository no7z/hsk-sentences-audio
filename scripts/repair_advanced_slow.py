"""Stage (and optionally apply) the selected PCM-atempo fix to band 7-9 only.

Recreates native PCM with the original seed and proves the normal MP3 is
byte-identical before deriving each slow file. Keeps all replaced slow files.
Requires the existing WSL CosyVoice environment and its cached normalizer.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.tts import CosyVoiceTTS
from scripts.diagnose_slow_audio import reset_seed


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def snapshot():
    return {p.name: digest(p) for p in (ROOT / 'dist/audio').glob('*.mp3')}


def duration(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    import torch
    if not torch.cuda.is_available():
        raise SystemExit('CUDA required; reuse the existing WSL environment')
    out = args.output.resolve()
    if (ROOT / '.local').resolve() not in out.parents:
        raise SystemExit('Repair output must be inside this repository .local/')
    out.mkdir(parents=True, exist_ok=False)
    staged, backup = out / 'staged', out / 'backup'
    staged.mkdir()
    backup.mkdir()
    source = ROOT / 'dist/sentences.json'
    source_hash = digest(source)
    records = [r for r in json.loads(source.read_text(encoding='utf-8')) if r['hsk_level'] == 7]
    if not records or any(not re.fullmatch(r'hsk7-\d{4}', r['id']) for r in records):
        raise SystemExit('Expected authored advanced records only')
    before = snapshot()
    manifest = {'method': 'native CosyVoice2 speed=1.0 PCM -> trim/fade -> atempo=0.8 -> MP3',
                'base_seed': 42, 'source_json_sha256': source_hash, 'before_audio': before,
                'status': 'staging', 'files': []}
    manifest_path = out / 'manifest.json'

    def save():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    save()
    import wetext.wetext as wetext_module
    cache = Path.home() / '.cache/modelscope/hub/pengzhendong/wetext'
    if not all((cache / language / 'tn' / name).is_file()
               for language in ('zh', 'en') for name in ('tagger.fst', 'verbalizer.fst')):
        raise SystemExit('Existing wetext cache required; no download attempted')
    with patch.object(wetext_module, 'snapshot_download', return_value=str(cache)):
        tts = CosyVoiceTTS(ROOT / 'data/reference/ref_female.wav',
                          (ROOT / 'data/reference/ref_female.txt').read_text(encoding='utf-8').strip())
    # Exactly reproduce the batch that was generated with no TN frontend.
    tts._model.frontend.text_frontend = ''
    audio = ROOT / 'dist/audio'
    for idx, record in enumerate(records, 1):
        sid = record['id']
        normal, slow = audio / f'{sid}.mp3', audio / f'{sid}_slow.mp3'
        if not normal.is_file() or not slow.is_file():
            raise SystemExit(f'Existing pair required: {sid}')
        reset_seed(int.from_bytes(sha256(f'42:{sid}'.encode()).digest()[:4], 'big'))
        with tempfile.TemporaryDirectory(prefix='hsk-slow-repair-') as folder:
            raw, proof = Path(folder) / 'native.wav', Path(folder) / 'normal.mp3'
            tts._synth_raw(record['chinese'], 1.0, str(raw))
            tts._encode(raw, proof, speed=1.0)
            if digest(proof) != before[normal.name]:
                raise SystemExit(f'Normal reconstruction differs; original files untouched: {sid}')
            candidate = staged / slow.name
            tts._encode(raw, candidate, speed=0.8)
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(candidate), '-f', 'null', '-'], check=True)
        ratio = duration(candidate) / duration(normal)
        if not 1.18 <= ratio <= 1.35:
            raise SystemExit(f'Unexpected tempo ratio; original files untouched: {sid}: {ratio}')
        manifest['files'].append({'id': sid, 'file': slow.name, 'normal_sha256': before[normal.name],
                                  'old_slow_sha256': before[slow.name], 'new_slow_sha256': digest(candidate),
                                  'slow_normal_duration_ratio': ratio})
        save()
        print(f'{idx}/{len(records)} {sid}: normal byte-identical; slow staged ({ratio:.4f}x)', flush=True)
    if digest(source) != source_hash or snapshot() != before:
        raise SystemExit('Source or audio changed during staging; nothing applied')
    manifest['status'] = 'staged'
    save()
    if args.apply:
        # Back up every old slow before the first replacement.
        for f in manifest['files']:
            shutil.copy2(audio / f['file'], backup / f['file'])
            if digest(backup / f['file']) != f['old_slow_sha256']:
                raise SystemExit('Backup verification failed; nothing applied')
        manifest['status'] = 'applying'
        save()
        applied = []
        try:
            for f in manifest['files']:
                dest = (audio / f['file']).resolve()
                if dest.parent != audio.resolve() or not dest.name.startswith('hsk7-'):
                    raise ValueError('Unsafe repair destination')
                if digest(dest) != f['old_slow_sha256']:
                    raise ValueError(f'Original slow changed before replacement: {dest.name}')
                os.replace(staged / f['file'], dest)
                applied.append(f)
            after = snapshot()
            expected = {**before, **{f['file']: f['new_slow_sha256'] for f in manifest['files']}}
            if after != expected:
                raise ValueError('Changes outside the intended slow-file set')
        except BaseException:
            for f in applied:
                tmp = audio / f".synth-rollback-{f['file']}"
                shutil.copy2(backup / f['file'], tmp)
                os.replace(tmp, audio / f['file'])
            manifest['status'] = 'rolled_back'
            save()
            raise
        manifest['status'] = 'applied'
        manifest['only_expected_slow_files_changed'] = True
        manifest['replaced_files'] = len(applied)
        save()
    print(json.dumps({'status': manifest['status'], 'slow_files': len(manifest['files']),
                      'backup': str(backup)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
