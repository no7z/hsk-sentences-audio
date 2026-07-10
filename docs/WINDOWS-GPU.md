# 在 Windows 11 + NVIDIA GPU 上跑音频合成

音频合成是整个管线最慢的一环（Mac CPU 约 8 秒/句对）。放到有 N 卡的 PC 上跑
CUDA 推理，预计 1-2 秒/句对，**提速 4-8 倍**。

## 分工设计

- **Mac（或任意机器）**：文本管线（句子/拼音/分词/校验），生成 `dist/sentences.json` 并提交
- **PC（GPU）**：只当"音频工人"——读 `dist/sentences.json`，合成缺失的 `dist/audio/*.mp3`，提交
- 通过 git 同步；音频文件名由句子 id 决定，`scripts/synth_audio.py` 自动跳过已存在的音频对，两边不会冲突

## PC 端安装（二选一）

### 方案 A：WSL2（推荐，坑最少）

CUDA 在 WSL2 里原生可用（需 Windows 端装好 NVIDIA 驱动），Linux 环境安装最顺：

```bash
# WSL2 Ubuntu 内
sudo apt install ffmpeg sox git
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
# python 3.10 环境（conda 或 uv 均可）
pip install -r requirements.txt          # Linux 平台守卫自动生效
# 下载模型
python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')"
```

### 方案 B：原生 Windows

CosyVoice 的 requirements 自带 win32 守卫（deepspeed/tensorrt 仅 Linux），原生可跑：

```powershell
# 需要: Python 3.10、git、ffmpeg（winget install ffmpeg）、CUDA 版 PyTorch
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121   # CUDA 轮子
# 模型下载同上
```

已知坑：老版 `openai-whisper==20231117` 构建失败时，改装最新版 `pip install openai-whisper`。

## 运行

```bash
# 克隆本数据集仓库
git clone <本仓库>
cd hsk-sentences-audio
pip install soundfile   # synth 工人只需这个 + CosyVoice 环境

# 指向 CosyVoice 位置
export COSYVOICE_REPO=/path/to/CosyVoice     # Windows: set COSYVOICE_REPO=C:\path\to\CosyVoice

# 先看缺哪些（不合成）
python scripts/synth_audio.py --dry-run

# 合成（自动用 CUDA；断点续跑，随时中断随时继续）
python scripts/synth_audio.py
# 或只跑某一级: python scripts/synth_audio.py --level 3

# 完成后提交音频
git add dist/audio && git commit -m "audio: HSK<N> synthesized on GPU" && git push
```

## 验证清单

- 启动日志应显示 `推理设备: CUDA:<你的显卡>`；若显示 CPU，检查 `torch.cuda.is_available()`
- 抽听几个 mp3；开头应无杂音（后处理裁 70ms+淡入在 `lib/tts.py`，两端一致）
- 速度参考：GPU 正常应在 1-3 秒/句对；超过 5 秒说明没走 CUDA
