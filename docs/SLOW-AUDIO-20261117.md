# 高等试制批次慢速音色排查

用户报告：新生成的常速正常，慢速有明显电音/金属感。此前的完整解码、
字错率和时长比检查不能证明音色自然，本次单独检查降速链路。

## 已确认的证据

- 旧版本和本次原生慢速都使用 CosyVoice2 的 `speed=0.8`，MP3 编码参数未变。
  不能简单归因为换了模型或编码器，也未证明固定随机种子是唯一原因。
- 原安装的 CosyVoice 提交为 `074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc`。
  其 [CosyVoice2 降速代码](https://github.com/QwenAudio/CosyVoice/blob/074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc/cosyvoice/cli/model.py#L320-L323)
  在进入 HiFT 声码器之前用线性插值拉长 mel 特征。
- 对 `hsk7-0001`、`hsk7-0045`、`hsk7-0120` 的常速和原生慢速进行了重新合成，
  六个 MP3 均与当前文件逐字节一致；因此对照确实重现了被报告的生成链路。
- 对照另含更换随机种子、原生 0.9 倍、PCM `atempo=0.8`、Rubber Band 两种设置，
  以及旧 `hsk6-0001` 的原始音频。共 36 份 MP3 解码检查未发现越过满刻度的采样，
  未见削波证据。基频统计只是描述值，不能用来证明电音消失。
- 用户对同一句 A（现有原生慢速）和 B（常速 PCM 经 atempo 降速）明确选择：
  **B 更自然、电音更少**。这是本次选择修复方法的听感依据。

据此将修复集中在降速处理：绕过原生 mel 拉伸，使用用户已试听的 B 方案。
这并未证明所有原生慢速都存在同一程度的伪影，也未把自动转写通过当作音色验收。

## 修复方式

```text
CosyVoice2 原生常速（speed=1.0）
  → 未压缩 PCM
  → 裁 70ms、淡入 30ms
  → FFmpeg atempo=0.8
  → 首次编码 MP3（24kHz、单声道、qscale=2）
```

[FFmpeg 官方文档](https://ffmpeg.org/ffmpeg-filters.html#atempo)给出了 `atempo=0.8`
作为 80% 速度的用法。本次直接处理未压缩波形，不把已有 MP3 解码后再次有损编码。

`lib/tts.py` 的默认慢速路径已改为上述处理，`_synth_raw()` 保留原生 speed 参数供对照实验。
新增回归测试保证慢速也只向模型传 `1.0`，随后在 PCM 上加入 `atempo=0.8`；
常速不加入 tempo 滤镜，已有文件仍禁止覆盖。

批次重做由 `scripts/repair_advanced_slow.py` 执行：每句使用原种子重建常速 PCM，
先证明按原参数编码的常速 MP3 与已有常速逐字节相同，再用该 PCM 产生慢速候选。
全部候选完整解码、时长比检查通过，且全部原始文件指纹仍相符，才备份并替换
`hsk7-xxxx_slow.mp3`。应用异常时恢复已替换的文件。

只处理本批 128 个高等慢速文件；常速文件、1–6 级文件、参考音色不参与替换。
原慢速备份和逐文件校验值位于本机
`.local/slow-audio-diagnosis/repair-atempo-v1/backup/` 及 `manifest.json`。
对照原始 WAV/MP3 和实验记录在 `.local/slow-audio-diagnosis/controlled-v1/`。

复现对照（输出必须在 dist 之外；脚本复用已有 normalizer 缓存，禁止隐式更新）：

```bash
export COSYVOICE_REPO="$HOME/CosyVoice"
export PATH="$HOME/.local/bin:$PATH"
~/CosyVoice/.venv/bin/python scripts/diagnose_slow_audio.py --output .local/slow-audio-diagnosis/new-comparison
```

批次最终替换数、保护结果和重跑后的筛查结果见 `slow-audio-repair.json`；
人工完整听审仍是独立步骤。

## 修复后核验

- 128 个常速 PCM 重建结果均能编码成与现有常速逐字节相同的 MP3。
- 实际仅替换 128 个 `hsk7-xxxx_slow.mp3`，128 份原慢速备份完整。
- 原有 8,708 个音频、全部高等常速文件及参考音色保持原哈希。
- 256 个新批次音频完整解码、格式和时长检查通过，慢速/常速比为
  1.2359–1.2490，中位数 1.2444；MP3 编码延迟和短片段边界使观测比例略有差异。
- 17 个 Python 测试、浏览器/导出与加载器检查通过。
- 转写重跑有 24 句超过字错率阈值，共 36 个文件（常速 17、慢速 19）。
  这些差异仍需逐句听审，不用于宣称电音得到自动量化或全部发音已经验收。
