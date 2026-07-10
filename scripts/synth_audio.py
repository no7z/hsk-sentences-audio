# -*- coding: utf-8 -*-
"""音频合成工人（可独立于文本管线运行，适合放到有 GPU 的机器上跑）。

只读 dist/sentences.json（文本真相源，由主管线在别处生成并提交），
为缺音频的句子合成 dist/audio/<id>.mp3 + <id>_slow.mp3。
- 断点续跑：已存在的音频对自动跳过
- 设备自动：有 CUDA 用 CUDA（GPU 约 1-2 秒/句对），否则 CPU（约 8 秒/句对）
- 不依赖 CC-CEDICT / jieba / HSK 词表——只需要 CosyVoice + ffmpeg

用法：
  python scripts/synth_audio.py                # 合成所有缺失音频
  python scripts/synth_audio.py --level 2      # 只合成某一级
  python scripts/synth_audio.py --dry-run      # 只列出缺哪些，不合成

环境变量：
  COSYVOICE_REPO  CosyVoice 仓库路径（含 pretrained_models/CosyVoice2-0.5B）
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=None, help="只合成某一 HSK 级")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    recs = json.loads((ROOT / "dist/sentences.json").read_text(encoding="utf-8"))
    if args.level:
        recs = [r for r in recs if r["hsk_level"] == args.level]
    audio_dir = ROOT / "dist/audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    todo = [r for r in recs
            if not ((audio_dir / f"{r['id']}.mp3").exists()
                    and (audio_dir / f"{r['id']}_slow.mp3").exists())]
    print(f"句子 {len(recs)}，缺音频 {len(todo)}")
    if args.dry_run or not todo:
        for r in todo[:20]:
            print(" ", r["id"], r["chinese"])
        return

    try:
        import torch
        dev = "CUDA:" + torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    except Exception:
        dev = "未知"
    print(f"推理设备: {dev}")

    from lib.tts import CosyVoiceTTS
    ref_wav = ROOT / "data/reference/ref_female.wav"
    ref_txt = (ROOT / "data/reference/ref_female.txt").read_text(encoding="utf-8").strip()
    tts = CosyVoiceTTS(ref_wav, ref_txt)

    t0 = time.time()
    for i, r in enumerate(todo, 1):
        tts.synth(r["chinese"], str(audio_dir / f"{r['id']}.mp3"), speed=1.0)
        tts.synth(r["chinese"], str(audio_dir / f"{r['id']}_slow.mp3"), speed=0.8)
        el = time.time() - t0
        eta = el / i * (len(todo) - i)
        print(f"  ♪ {i}/{len(todo)} {r['id']} {r['chinese']}  ({el/i:.1f}s/句, 剩约{eta/60:.0f}分)")
    print(f"完成：{len(todo)} 句，用时 {(time.time()-t0)/60:.1f} 分钟")


if __name__ == "__main__":
    main()
