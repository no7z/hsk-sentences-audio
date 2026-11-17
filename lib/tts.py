# -*- coding: utf-8 -*-
"""TTS 合成 + 音频后处理。

引擎：CosyVoice2-0.5B（Apache-2.0，本地 CUDA/CPU）。零样本音色 = 录音棚中文女参考音频
（data/reference/ref_female.wav，由 scripts/make_reference.py 用 CosyVoice-300M-SFT 生成并缓存）。

音频后处理（原型听测选定“强档”）：裁掉开头 70ms（去 CosyVoice 零样本 onset 瞬态杂音）
+ 30ms 淡入。慢速从原生常速 PCM 经 atempo=0.8 降速后再编码 MP3。
"""
import os
import subprocess
import sys
import tempfile
import math
import hashlib
import random
from contextlib import nullcontext
from unittest.mock import patch
from pathlib import Path

# CosyVoice 安装位置（用户按其官方说明安装；默认指向原型环境）
COSYVOICE_REPO = os.environ.get(
    "COSYVOICE_REPO",
    str(Path.home() / "projects/new/ideas/tts-lab/CosyVoice"),
)
TRIM_START = 0.070   # 裁掉开头秒数（去 onset 杂音）
FADE_IN = 0.030      # 淡入秒数


def seed_sentence(sentence_id, base_seed=42):
    """Stable random state shared by both renderings of an authored sentence."""
    import numpy as np
    import torch
    value = int.from_bytes(hashlib.sha256(f"{base_seed}:{sentence_id}".encode()).digest()[:4], "big")
    random.seed(value)
    np.random.seed(value)
    torch.manual_seed(value)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(value)
    return value


class CosyVoiceTTS:
    def __init__(self, ref_wav, ref_text, model="CosyVoice2-0.5B"):
        self.ref_wav = str(ref_wav)
        self.ref_text = ref_text
        sys.path.insert(0, COSYVOICE_REPO)
        sys.path.insert(0, str(Path(COSYVOICE_REPO) / "third_party/Matcha-TTS"))
        from cosyvoice.cli.cosyvoice import AutoModel  # noqa: E402
        import torchaudio  # noqa: E402
        self._torchaudio = torchaudio
        # Existing wetext versions otherwise query/download their repository on
        # every model initialization. Reuse the installed cache, or let CosyVoice
        # fall back to its built-in plain-text handling without a network call.
        try:
            import wetext.wetext as wetext_module
        except ImportError:
            normalizer_context = nullcontext()
        else:
            cache = Path(os.environ.get("WETEXT_MODEL_DIR", str(Path.home() / ".cache/modelscope/hub/pengzhendong/wetext")))
            def existing_normalizer(*args, **kwargs):
                if not all((cache / language / 'tn' / name).is_file()
                           for language in ('zh', 'en') for name in ('tagger.fst', 'verbalizer.fst')):
                    raise FileNotFoundError(f"Existing wetext cache unavailable: {cache}")
                return str(cache)
            normalizer_context = patch.object(wetext_module, "snapshot_download", side_effect=existing_normalizer)
        with normalizer_context:
            self._model = AutoModel(
                model_dir=str(Path(COSYVOICE_REPO) / "pretrained_models" / model))

    def _synth_raw(self, text, speed, out_wav):
        # The frontend can split longer sentences even with stream=False.
        # Saving only the first yield silently truncates advanced material.
        import torch
        chunks = [j["tts_speech"].cpu() for j in self._model.inference_zero_shot(
            text, self.ref_text, self.ref_wav, stream=False, speed=speed)]
        if not chunks:
            raise RuntimeError("CosyVoice returned no speech")
        self._torchaudio.save(out_wav, torch.cat(chunks, dim=-1), self._model.sample_rate)

    def _encode(self, raw_wav, out_mp3, speed=1.0):
        """Encode PCM with waveform tempo adjustment; never stretch model mels."""
        if not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
            raise ValueError("Audio tempo must be between 0.5 and 2.0")
        dest = Path(out_mp3)
        if dest.exists():
            raise FileExistsError(f"Refusing to overwrite existing audio: {dest}")
        # Local temporary storage avoids WSL /mnt/d raw-WAV I/O. Publish a
        # complete MP3 only, so an interrupted encoder is never resume-skipped.
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, staging = tempfile.mkstemp(suffix=".mp3", prefix=".synth-", dir=dest.parent)
        os.close(fd)
        try:
            af = (f"atrim=start={TRIM_START},asetpts=PTS-STARTPTS,"
                  f"afade=t=in:st=0:d={FADE_IN}")
            if speed != 1.0:
                af += f",atempo={speed}"
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_wav),
                 "-af", af, "-codec:a", "libmp3lame", "-qscale:a", "2", staging],
                check=True)
            # link is atomic and fails if another worker already published it.
            os.link(staging, dest)
        finally:
            Path(staging).unlink(missing_ok=True)

    def synth(self, text, out_mp3, speed=1.0):
        """Synthesize at native speed, then change tempo on uncompressed PCM.

        CosyVoice2's native speed control interpolates mel features before its
        vocoder, which can introduce metallic timbre. Keep the vocoder at 1.0
        and apply the user-selected atempo method before the first MP3 encode.
        """
        if Path(out_mp3).exists():
            raise FileExistsError(f"Refusing to overwrite existing audio: {out_mp3}")
        if not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
            raise ValueError("Audio tempo must be between 0.5 and 2.0")
        with tempfile.TemporaryDirectory(prefix="hsk-tts-") as tmpdir:
            raw = Path(tmpdir) / "speech.wav"
            self._synth_raw(text, 1.0, str(raw))
            self._encode(raw, out_mp3, speed=speed)

    def synth_pair(self, text, normal_mp3, slow_mp3):
        """Infer native PCM once, then publish only missing members of the pair."""
        normal, slow = Path(normal_mp3), Path(slow_mp3)
        if normal.resolve() == slow.resolve():
            raise ValueError("Normal and slow destinations must differ")
        if normal.exists() and slow.exists():
            return
        with tempfile.TemporaryDirectory(prefix="hsk-tts-pair-") as folder:
            raw = Path(folder) / "native.wav"
            self._synth_raw(text, 1.0, str(raw))
            if not normal.exists():
                self._encode(raw, normal, speed=1.0)
            if not slow.exists():
                self._encode(raw, slow, speed=0.8)
