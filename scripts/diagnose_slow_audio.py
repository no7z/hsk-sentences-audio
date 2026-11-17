"""Generate controlled slow-audio comparisons without touching dist/ assets.

Run with the existing CosyVoice WSL Python. Every variant uses the same text,
model and reference; native mel-speed and waveform-speed changes are isolated.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.tts import CosyVoiceTTS, TRIM_START, FADE_IN


def reset_seed(value):
    import numpy as np
    import torch
    random.seed(value)
    np.random.seed(value)
    torch.manual_seed(value)
    torch.cuda.manual_seed_all(value)


def encode(raw, dest, tempo_filter=None):
    filters = [f"atrim=start={TRIM_START}", "asetpts=PTS-STARTPTS", f"afade=t=in:st=0:d={FADE_IN}"]
    if tempo_filter:
        filters.append(tempo_filter)
    subprocess.run(["ffmpeg", "-n", "-v", "error", "-i", str(raw), "-af", ','.join(filters),
                    "-codec:a", "libmp3lame", "-qscale:a", "2", str(dest)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids", nargs="+", default=["hsk7-0001", "hsk7-0045", "hsk7-0120", "hsk6-0001"])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    output = args.output.resolve()
    if output == (ROOT / 'dist').resolve() or (ROOT / 'dist').resolve() in output.parents:
        raise SystemExit("Diagnostic output must stay outside dist/")
    output.mkdir(parents=True, exist_ok=True)
    records = {r['id']: r for r in json.loads((ROOT / 'dist/sentences.json').read_text(encoding='utf-8'))}
    before = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
              for p in (ROOT / 'dist/audio').glob('*.mp3')}
    ref = ROOT / 'data/reference'
    # The batch under investigation fell back to no external text normalizer.
    # Avoid wetext's implicit remote updates while recreating that condition.
    import wetext.wetext as wetext_module
    cache = Path.home() / '.cache/modelscope/hub/pengzhendong/wetext'
    if not all((cache / language / 'tn' / name).is_file()
               for language in ('zh', 'en') for name in ('tagger.fst', 'verbalizer.fst')):
        raise SystemExit(f'Existing wetext cache required; will not download: {cache}')
    with patch.object(wetext_module, 'snapshot_download', return_value=str(cache)):
        tts = CosyVoiceTTS(ref / 'ref_female.wav', (ref / 'ref_female.txt').read_text(encoding='utf-8').strip())
    tts._model.frontend.text_frontend = ''
    items = []
    for sid in args.ids:
        record = records[sid]
        folder = output / sid
        folder.mkdir(exist_ok=False)
        for speed, name in record['audio'].items():
            shutil.copy2(ROOT / 'dist' / name, folder / f'current_{speed}.mp3')
        seed = int.from_bytes(sha256(f'42:{sid}'.encode()).digest()[:4], 'big')
        variants = [('normal', 1.0, seed), ('native_slow_same_seed', 0.8, seed),
                    ('native_slow_other_seed', 0.8, (seed + 104729) % 2**32),
                    ('native_mild_same_seed', 0.9, seed)]
        files = {}
        for label, speed, value in variants:
            reset_seed(value)
            raw = folder / f'{label}.wav'
            tts._synth_raw(record['chinese'], speed, str(raw))
            dest = folder / f'{label}.mp3'
            encode(raw, dest)
            files[label] = dest.name
            print(f'{sid}: {label}', flush=True)
        for label, filt in [('wave_atempo', 'atempo=0.8'),
                            ('wave_rubberband', 'rubberband=tempo=0.8:pitch=1'),
                            ('wave_rubberband_smooth', 'rubberband=tempo=0.8:pitch=1:transients=smooth:detector=soft:window=long:smoothing=on')]:
            dest = folder / f'{label}.mp3'
            encode(folder / 'normal.wav', dest, filt)
            files[label] = dest.name
        items.append({'id': sid, 'chinese': record['chinese'], 'seed': seed, 'variants': files,
                      'normal_reproduces_current_mp3': sha256((folder / 'normal.mp3').read_bytes()).hexdigest() == sha256((folder / 'current_normal.mp3').read_bytes()).hexdigest(),
                      'native_slow_reproduces_current_mp3': sha256((folder / 'native_slow_same_seed.mp3').read_bytes()).hexdigest() == sha256((folder / 'current_slow.mp3').read_bytes()).hexdigest()})
    after = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
             for p in (ROOT / 'dist/audio').glob('*.mp3')}
    info = {'model': 'CosyVoice2-0.5B', 'text_normalizer': 'disabled to reproduce the investigated batch',
            'dist_audio_unchanged': before == after, 'samples': items}
    (output / 'experiment.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=2))
    if before != after:
        raise SystemExit('Original audio changed during diagnosis')


if __name__ == '__main__':
    main()
