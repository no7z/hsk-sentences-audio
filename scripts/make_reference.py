# -*- coding: utf-8 -*-
"""生成并缓存“录音棚中文女”参考音频（一次性）。

用 CosyVoice-300M-SFT 的内置说话人 '中文女' 合成一句干净参考音频，供 CosyVoice2-0.5B
零样本合成克隆音色。参考音频 + 其文本缓存到 data/reference/。全程 Apache-2.0，可随仓库分发。

用法： python scripts/make_reference.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COSYVOICE_REPO = os.environ.get(
    "COSYVOICE_REPO", str(Path.home() / "projects/new/ideas/tts-lab/CosyVoice"))
REF_TEXT = "今天天气很好，我们一起去公园散步吧。"
REF_DIR = ROOT / "data/reference"


def main():
    sys.path.insert(0, COSYVOICE_REPO)
    sys.path.insert(0, str(Path(COSYVOICE_REPO) / "third_party/Matcha-TTS"))
    from cosyvoice.cli.cosyvoice import AutoModel
    import torchaudio

    REF_DIR.mkdir(parents=True, exist_ok=True)
    m = AutoModel(model_dir=str(Path(COSYVOICE_REPO) / "pretrained_models/CosyVoice-300M-SFT"))
    for _, j in enumerate(m.inference_sft(REF_TEXT, "中文女", stream=False)):
        torchaudio.save(str(REF_DIR / "ref_female.wav"), j["tts_speech"], m.sample_rate)
        break
    (REF_DIR / "ref_female.txt").write_text(REF_TEXT, encoding="utf-8")
    print("参考音频已缓存:", REF_DIR / "ref_female.wav")


if __name__ == "__main__":
    main()
