# 原标准高等 7–9 档补全记录

本阶段只补《国际中文教育中文水平等级标准》GF0025-2021 的高等合并档。
`hsk_level: 7`、`hsk7-xxxx` 是合并档的存储代码，不表示单独七级。
目前是 **318 句阶段语料，高等全量补齐尚未完成**，不应对外宣称已覆盖全部原标准。

本轮结果：新增 636 个双速 MP3，工作目录共 4,672 句、9,344 个音频。
636 个新文件完整解码及格式检查通过。所有新增慢速采用用户选择的波形降速方案，
慢速/常速时长比为 1.2333–1.2490，中位数 1.2435。
Whisper small 筛查 46 句超过字错率阈值（常速 34 个、慢速 38 个文件）；
它们是待听审样本，不是已经确认的音频错误，也不是已通过听审的成品。
另有词表未收录的输出词形，最新逐项清单见 `advanced-progress.json`，需词汇范围审核。
重点听审索引见 [advanced-listening-review.md](advanced-listening-review.md)，
原始双速转写及文件指纹见 [advanced-audio-check.json](advanced-audio-check.json)。

本地验证：17 个 Python 测试、36 条语法断言、8 个浏览器/导出测试、
3 个 npm 加载器测试和 3 个 Python 加载器测试通过；版本基线核验通过。
这些是程序与数据完整性检查，不代替语言质量验收。

## 接手基线与保护

- 接手时工作区干净，本地停在 `667f76d`；已保留分支
  `codex/pre-advanced-local-20261117`，随后快进至远端 `df380e0`（v1.1.0）。
- 工作分支为 `codex/gf2021-advanced`。本阶段未推送、合并或发布。
- 原有 4,354 条记录的所有字段保持不变，包括原等级、ID、中文、译文、拼音及考试词汇估算。
- 原有 8,708 个 MP3 和 `data/reference/` 两个参考文件保持逐字节不变。
- 版本基线摘要保存在 `data/baselines/v1.1.0.json`；完整逐文件哈希和旧 JSON
  另存本机 `.local/advanced-baseline/`。`audit_advanced.py` 每次均核对版本基线，
  加上 `--baseline .local/advanced-baseline` 可给出本机逐项差异。
- `build.py --level 7` 只重建高等档；已存在高等 ID 的中文、译文或数量若被改动，构建会拒绝。
  后续批次必须在 YAML 尾部追加。元数据可以校正；变更音频对应文本须另行安排迁移。

## 标准、词表和完成口径

教育部原版 PDF 的第 2 页把 1–3 级列为初等、4–6 级列为中等，7–9 级为高等。
高等新增 5,636 个词语项目，累计 11,092；量化指标不再按 7、8、9 级分别细分。
PDF 文件 SHA256、抽查范围、下载链接和社区来源均记录在
`data/standards/gf0025-2021-7-9.source.json`。

本次固定 `krmanik/HSK-3.0` 的 2021 路径及提交
`5a7a6111fe4ff0d5fa98f06ffb440af10627a927`：5,636 行、5,620 种字形。
原项目下载的 `new_7.json` 只有 5,606 种字形；与新快照相比缺 18 种、多 4 种。
不能把这两个词表的数字混用，更不能把 5,620 种字形直接叫作 5,636 个词义项目。
现已逐行核对官方扫描件中的全部 5,636 个字形：5,396 行经两轮 OCR 与转录一致，
其余 240 行已在官方扫描件裁图中逐项目视核对，未发现字形差异。
证据摘要、手工核对行号和文件指纹见 `data/standards/gf0025-2021-7-9.verification.json`。
此核对仅确认字形与顺序，不表示已完整核验所有读音、括号限定、义项或句子分级。

`docs/advanced-progress.json` 给出机器可复算的阶段状态、全部缺词、未收录词及分词问题。
当前 318 句自动分词覆盖 603/5,620 种高等字形（约 10.73%），其中刻意标注的目标字形有 464 种。
旧 1–6 级句子偶然出现的高等字形另计，不能算作新增高等句子。
重复字形的不同读音/义项、148 个高等语法点、词汇范围和最终听审仍待逐项审核。
本批不作“零未收录词”或“已完成高等语法覆盖”的声明。

## 后续文本生成与质量门槛

用户已明确要求质量优先，可以补充 AI Gateway 额度。此前 DeepSeek V3.1 起草、
Gemini 2.5 Flash 复核的 20 句试跑暴露了拼音格式、语境释义、英文和漏审问题，
整批被拒绝，未进入正式数据或音频生成。

已对 Claude Opus 5.5、Claude Fable 5.2 做相同的 16 项难词对照，主代理逐句阅读
两组共 32 条结果，再由 GPT-6 Astra 在隐藏作者身份后独立审查。
另混入 6 条已知错误与 6 条合格对照：Astra 识别全部 6 条错误并保留全部 6 条合格句。
这只是小样本校准，不证明全量零错误或通用模型排名。详见 `advanced-model-selection.json`。

后续采用 Claude Fable 5.2 起草、GPT-6 Astra 独立复核，均为 high reasoning effort。
新流程首批 20 句已通过主代理逐句阅读；Astra 修正了一处儿化拼音（冰棍儿 → bīng gùnr）。
它们仍是下一批完整作业的草稿，尚未入库。各批须通过格式、目标词和重复检查，
逐项独立复核、主代理接纳、构建注音/释义检查，才进入本地双速音频生成。
模型断点和请求费用存于本机忽略目录 `.local/advanced-bulk/gateway/`；
密钥只在本机 `.env.local`，不会写入数据、代码或请求日志。余额不足时保留断点，
不会自动充值、切换低质量模型或将未审稿件入库。

4,000–6,000 句仍只是先前估算，不作为凑数指标。目前样本不足以核定全量句数，
应先核对词表，再按缺词的自然搭配、必要词义和场景补句；尾部难词往往需要独立语境，
不可把首批平均覆盖数简单线性外推。避免用词语堆砌、释义模板或生硬长句换覆盖率。

## 已复用的 Windows/WSL 环境

实际成功生成旧音频的是 **WSL2 Ubuntu**：

| 项目 | 实测位置或版本 |
|---|---|
| Python | `/home/xylopen/CosyVoice/.venv/bin/python` |
| PyTorch | `2.3.1+cu121`，CUDA 可用 |
| 模型仓库 | `/home/xylopen/CosyVoice` |
| 本次模型 | `pretrained_models/CosyVoice2-0.5B`，原权重完整 |
| GPU | RTX 3080 Ti，12 GB |
| 参考音色 | 本仓库 `data/reference/ref_female.wav` 与 `.txt` |
| 旧启动脚本 | WSL `~/run_synth.sh` → `~/synth_fast.py` |
| 旧任务日志 | WSL `~/synth.log`，旧短句约 5.1 秒/句对 |
| ASR 筛查 | 原环境已有 Whisper 与 `~/.cache/whisper/small.pt` |

没有重装 CosyVoice、PyTorch、CUDA、模型或参考音色。Windows 系统 Python 的
`2.5.1+cu121` 也支持 CUDA，但不是本次 TTS 启动环境。
缺失的文本依赖装在独立 `.venv-text`，未装入原 TTS 环境。
原国内 pip 镜像未返回所需包，文本依赖使用 PyPI 安装。

最初模型加载时 wetext 的远程版本查询返回 403，曾回退为无外部文本规范化前端。
目前已复用原 wetext 缓存，加载不再查询远程版本；同一试句的常速和 B 方案慢速
均与已认可样本逐字节一致。新句对只推理一次常速原始 PCM，再分别编码双速，
不覆盖已存在的任何音频；文本全部使用中文写法。

## 复现和继续追加

PowerShell 中可直接使用现有环境：

```powershell
# 原音频入口仍为 scripts/synth_audio.py；包装脚本只设置现有 WSL 环境。
wsl -d Ubuntu -- bash /mnt/d/dev/hsk/hsk-sentences-audio/scripts/run_audio_wsl.sh --level 7 --dry-run
wsl -d Ubuntu -- bash /mnt/d/dev/hsk/hsk-sentences-audio/scripts/run_audio_wsl.sh --level 7 --limit 2
wsl -d Ubuntu -- bash /mnt/d/dev/hsk/hsk-sentences-audio/scripts/run_audio_wsl.sh --level 7

# 文本依赖使用已有 .venv-text，勿重新运行 1–6 级构建。
$env:PYTHONUTF8='1'
.\.venv-text\Scripts\python.exe build.py --level 7 --no-audio
.\.venv-text\Scripts\python.exe scripts/enrich_exam_levels.py --write
.\.venv-text\Scripts\python.exe scripts/build_web.py
.\.venv-text\Scripts\python.exe scripts/audit_advanced.py --require-audio --output docs/advanced-progress.json
```

高等档的 `exam_vocab_level_2025` 明确留为 `null`，表示新版考试工作后置；
`enrich_exam_levels.py` 这里只刷新增量兼容元数据，不对这批进行新版大纲覆盖或重新分级。
旧记录的 422 条考试高等估算不变。npm/PyPI/Hugging Face 未更新版本或远端数据；
包准备脚本仅去除总数写死的限制，供现有 CI 验证追加记录兼容性。

音频合成使用 CosyVoice2、同参考音色、裁 70ms、淡入 30ms、24kHz 单声道 MP3。
2026-11-17 用户对照试听选择波形降速方案后，新高等档慢速改为模型按 1.0 合成原生 PCM，
再经 `atempo=0.8` 降速；不再向声码器传原生 `speed=0.8`。
详见 [慢速音色排查与修复](SLOW-AUDIO-20261117.md)。原有 1–6 级音频保留。
本次还修复了长句只保存首段、缺一半音频时
覆盖已有另一半的问题；临时编码完成后才原子发布，并为双速固定同一句随机种子，
避免独立随机生成导致“慢速”反而更快。中断后重跑同一命令，只补缺失文件。

完整音频筛查命令（WSL，复用已缓存的 small 模型，不会下载新模型）：

```bash
export PATH="$HOME/.local/bin:$PATH"
~/CosyVoice/.venv/bin/python scripts/check_advanced_audio.py --asr --output docs/advanced-audio-check.json
```

该命令验证所有新 MP3 完整解码、格式、时长比，并记录双速转写和字错率。
字错率大于 0.15 或时长比不在 1.18–1.35 会标记复核；同音字、语音自然度、
词义和细微声调问题可能不会触发阈值，不能把通过自动筛查称作人工听审通过。

下一步以 `advanced-progress.json` 的缺词清单和语义/词义审核为依据追加，
优先处理未覆盖目标词、同形不同读音/义项及当前未收录词；审核文本后再运行音频工人。
