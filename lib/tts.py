# -*- coding: utf-8 -*-
"""TTS 合成 + 音频后处理。

引擎：CosyVoice2-0.5B（Apache-2.0，本地 CPU）。零样本音色 = 录音棚中文女参考音频
（data/reference/ref_female.wav，由 scripts/make_reference.py 用 CosyVoice-300M-SFT 生成并缓存）。

音频后处理（原型听测选定“强档”）：裁掉开头 70ms（去 CosyVoice 零样本 onset 瞬态杂音）
+ 30ms 淡入，输出 mp3。
"""
import os
import subprocess
import sys
from pathlib import Path

# CosyVoice 安装位置（用户按其官方说明安装；默认指向原型环境）
COSYVOICE_REPO = os.environ.get(
    "COSYVOICE_REPO",
    str(Path.home() / "projects/new/ideas/tts-lab/CosyVoice"),
)
TRIM_START = 0.070   # 裁掉开头秒数（去 onset 杂音）
FADE_IN = 0.030      # 淡入秒数


class CosyVoiceTTS:
    def __init__(self, ref_wav, ref_text, model="CosyVoice2-0.5B"):
        self.ref_wav = str(ref_wav)
        self.ref_text = ref_text
        sys.path.insert(0, COSYVOICE_REPO)
        sys.path.insert(0, str(Path(COSYVOICE_REPO) / "third_party/Matcha-TTS"))
        from cosyvoice.cli.cosyvoice import AutoModel  # noqa: E402
        import torchaudio  # noqa: E402
        self._torchaudio = torchaudio
        self._model = AutoModel(
            model_dir=str(Path(COSYVOICE_REPO) / "pretrained_models" / model))

    def _synth_raw(self, text, speed, out_wav):
        for _, j in enumerate(self._model.inference_zero_shot(
                text, self.ref_text, self.ref_wav, stream=False, speed=speed)):
            self._torchaudio.save(out_wav, j["tts_speech"], self._model.sample_rate)
            break

    def synth(self, text, out_mp3, speed=1.0):
        """合成一句并做后处理，输出 mp3。"""
        tmp = str(Path(out_mp3).with_suffix(".raw.wav"))
        self._synth_raw(text, speed, tmp)
        af = (f"atrim=start={TRIM_START},asetpts=PTS-STARTPTS,"
              f"afade=t=in:st=0:d={FADE_IN}")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", tmp,
             "-af", af, "-codec:a", "libmp3lame", "-qscale:a", "2", out_mp3],
            check=True)
        os.remove(tmp)
