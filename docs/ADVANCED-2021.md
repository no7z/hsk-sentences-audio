# 原标准高等 7–9 档补全记录

本阶段只补《国际中文教育中文水平等级标准》GF0025-2021 的高等合并档。
`hsk_level: 7`、`hsk7-xxxx` 是合并档的存储代码，不表示单独七级。
## 当前状态（2026-11-21）

| 项目 | 结果 |
|---|---|
| 高等句子 | **5,577 句**（`hsk7-0001`…`hsk7-5577`），每句 10–35 个汉字，平均 16.4 |
| 工作数据 | 共 9,931 条记录、19,862 个 MP3（旧 1–6 级 8,708 个 + 高等 11,154 个） |
| 词表字形覆盖 | **5,620/5,620**（`advanced-progress.json` 的 `missing_spellings` 为空）；其中 5,564 种是刻意标注的目标词 |
| 语法点覆盖 | **144/148**，每点至少 2 句候选例句；145–148 为句群，单句数据按设计不适用。见 [advanced-grammar-coverage.md](advanced-grammar-coverage.md) |
| 音频 | 每批 Whisper small 筛查，超阈值的句子换随机种子重生成；重试后仍标记的句子由维护者逐句试听确认 |
| 版本基线 | 旧 4,354 条记录只在 29 条的拼音字段上有改动（见下文），8,708 个 MP3 和参考音色逐字节不变；`audit_advanced.py` 按 `data/baselines/v1.2.0.json` 核对 |

尚未完成、因此**不是发布版**：

- **全量听审**：只有 ASR 标记过的句子经人工试听，其余音频只过了自动筛查。
- **词汇范围**：3,209 句里有 1,956 种分词结果不在任何官方词表（如 诠释、瑕疵、琳琅满目），
  903 句用到 471 个字表外汉字。高等是最高档，没有“超纲”可言，但这些词仍需人工审核；不作“零未收录词”声明。
- **语法标签**：语法覆盖只记在审计报告里，高等记录的 `grammar_points` 仍为空（导入校验要求另行审核语法 ID）。
- **读音/义项**：拼音由工具生成，已普查并修正明显误读，轻声已按官方词表统一（见下文“拼音”）；
  同形不同读音/义项没有逐条人工核对。

本地验证：pytest 28 项、浏览器/导出 node 测试 8 项、npm 加载器 3 项通过；
`audit_advanced.py --require-audio` 0 问题。这些是程序与数据完整性检查，不代替语言质量验收。

## 接手基线与保护

- 接手时工作区干净，本地停在 `667f76d`；已保留分支
  `codex/pre-advanced-local-20261117`，随后快进至远端 `df380e0`（v1.1.0）。
- 最初工作分支为 `codex/gf2021-advanced`，之后批量补句在 `feat/hsk7-advanced-first-batches` 上进行。
  截至本文更新，均未推送、合并或发布。
- 原有 4,354 条记录的原等级、ID、中文、译文、分词、词义及考试词汇估算保持不变；
  2026-11-21 经维护者同意，只修正了 29 条记录的拼音字段（见“拼音”一节）。
- 原有 8,708 个 MP3 和 `data/reference/` 两个参考文件保持逐字节不变。
- 已发布版本的指纹保存在 `data/baselines/v1.1.0.json`（不再改动）。拼音修正后的旧数据指纹在
  `data/baselines/v1.2.0.json`（随 GitHub v1.2.0 发布），其中逐条列出相对 v1.1.0 改了哪些记录、哪些读音；
  审计脚本以它为准（常量 `LEGACY_BASELINE`）。v1.1.0 的完整逐文件哈希和旧 JSON
  另存本机 `.local/advanced-baseline/`；用 `--baseline` 对照它时，这 29 条会列为改动。`audit_advanced.py` 每次均核对版本基线，
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
覆盖统计用 `hsk_validate.hsk_segment`（按 1–6 级词表加高等词表的最少词数最大匹配），
与构建时 jieba 分词不同；新句须两种分词都让目标词独立成词（工具见 `.local/advanced-bulk/tools/` 的 segcheck/audseg）。
旧 1–6 级句子偶然出现的高等字形另计，不能算作新增高等句子。
重复字形的不同读音/义项、词汇范围和最终听审仍待逐项审核；不作“零未收录词”声明。

148 个高等语法点由 `scripts/audit_advanced_grammar.py` 审计：单字虚词按 jieba token、固定格式按正则匹配，
每条规则在官方例句上自测；059/085/088/128 没有可靠的自动规则，例句为人工逐句判定（`MANUAL_EXAMPLES`）。
匹配是候选，不是语法判定。

## 后续文本生成与质量门槛

用户已明确要求质量优先，可以补充 AI Gateway 额度。此前 DeepSeek V3.1 起草、
Gemini 2.5 Flash 复核的 20 句试跑暴露了拼音格式、语境释义、英文和漏审问题，
整批被拒绝，未进入正式数据或音频生成。

已对 Claude Opus 5.5、Claude Fable 5.2 做相同的 16 项难词对照，主代理逐句阅读
两组共 32 条结果，再由 GPT-6 Astra 在隐藏作者身份后独立审查。
另混入 6 条已知错误与 6 条合格对照：Astra 识别全部 6 条错误并保留全部 6 条合格句。
这只是小样本校准，不证明全量零错误或通用模型排名。详见 `advanced-model-selection.json`。

早期曾试行 Claude Fable 5.2 起草、GPT-6 Astra 复核。实际批量生产采用的流程如下：

1. **分配**：词表按序切成 batch-01…28（一词一句，共约 5,300 个目标），再用 batch-29 补齐
   审计分词下仍未覆盖的 23 词；grammar-01…03 为语法点补句（仍各带一个词汇目标）。
2. **起草**：Claude Code 里的 Claude Opus 5.5 本地起草，每轮约 24 句；按 `import_advanced_batch.validate_batch`
   自检（10–50 个汉字、目标词原样出现、声调符号、topic 合法、不与已有句子重复）。
3. **预检**：送审前先过 build 同款分词和审计分词，目标词必须独立成词；离合词不拆开使用。
4. **复核**：GPT-6.1 Sol（high effort）独立审校，先经本机 Codex CLI，后改经 AI Gateway，每批带
   `--max-spend-usd` 上限。Sol 只能改中文、英文、topic、拼音和词义，不能换目标词。
5. **接纳**：主代理逐条看 Sol 的改动再决定是否接纳。常见拒绝理由：把「一」「不」写成变调
   （本项目统一标本调）、把单字目标吞进复合词、改成罕见义项、改掉了句子要演示的语法点。
   审批文件记录接纳稿的 sha256，导入脚本据此拒绝未经审批的稿件。
6. **导入与构建**：只在 YAML 尾部追加；`build.py --level 7 --refresh-from-id <新批首序号>` 只重算新句，
   再核对每个目标词在 `dist/sentences.json` 中独立成词且有拼音和词义。
7. **音频**：同一 CosyVoice2 参考音色本地合成；Whisper 筛查后对超阈值句换种子 43–47 重生成，
   仍不过的句子逐句送维护者试听，必要时再换种子。

模型断点和请求费用存于本机忽略目录 `.local/advanced-bulk/`；密钥只在本机 `.env.local`，
不会写入数据、代码或请求日志。

## 拼音

拼音来自 pypinyin 句级读音，叠加 CC-CEDICT 轻声/儿化词播种和人工覆盖
（`data/overrides.json`；高等另有 `data/advanced_overrides.json`，以及 YAML 中的句子级 `token_pinyin`）。
句子级键可写成「词#n」，只覆盖该词在句中第 n 次出现，用于重叠动词第二个字读轻声（如 `"看#2": "kan"`）。
数字调拼音 `pinyin_numbered` 一律由带调拼音换算（儿化合为一个音节，如 nar3），两者始终一致。
「一」「不」按官方词表体例标变调（2026-11-21 起，由 `lib/pinyin.apply_yi_bu_sandhi` 在构建时统一处理）：
不在四声前标 bú、A不A 中间标 bu；一在四声前标 yí、一二三声前标 yì、重叠动词中间（看一看）标 yi；
序数和号码（第一、初一、十一月、一月一日、一号、一楼、一年级、一等奖）及词末的「一」（统一、唯一、之一）保持 yī。
一动不动、爱理不理、时不时、独一无二 按固定读法处理。覆盖层（overrides、YAML）只需写本调。
共改 2,256 条记录（高等 1,644、旧 1–6 级 612），顺带修正 这不是／这不怪你／得不得了 里误标的轻声「不」。
轻声只用于必读轻声。

2026-11-21 规则修正（不花额度，逐句核对）：助词 了 le、过 guo（经历/完成）、的/地/得 de、着 zhe，量词 只 zhī，把 bǎ，好处 hǎo chù，真是 zhēn shì，可能补语里的 不 读轻声（拿不到、睡不着、进不了）；动词「过马路」「过得」、「得了金牌」、「地里」等按原读音保留。共改 245 条记录（高等 114、旧 1–6 级 131），写成句子级覆盖。之后计划用 Codex GPT-6.2 Sol 全量只读复核（200 句试跑：真错约 20 处，约占周额度 2%）。

**轻声的依据**是 GF0025-2021 官方词表的注音（与《现代汉语词典》体例一致）：不带调号的音节是必读轻声，写成轻声；
前有圆点、仍带调号的音节（如 学生 xué·shēng、关系 guān·xì、起来 qǐ·lái）是“一般轻读、间或重读”，按本项目约定写本调。
官方 PDF 没有文字层，用 Windows 自带的 PDF 渲染和 OCR 定位词条，再逐行目视核对拼音列：641 个词直接核对，
18 个 OCR 未能定位的词按同类词规律推断（如 姐姐 jiě jie、石头 shí tou）。
2026-11-21 据此改了 739 条记录（高等 541、旧 1–6 级 198）的拼音字段，例如 学生 sheng→shēng、起来 lai→lái、
别人 ren→rén、故事 shì→shi、心里 li→lǐ、照顾 gu→gù、合同 tong→tóng；同时修正 大夫 dài fu、当时 dāng shí 等误读。
同形多义词按句意分别处理：地方（地点 dì fang / 地方的 dì fāng）、精神（jīng shén / 有精神 jīng shen）、
地道（地道的 dì dao）、人家（rén jia / 户 rén jiā）、教会（教 jiāo huì）等，写成句子级覆盖。
意义固定的词写入 `data/overrides.json` 的 token_pinyin（新增约 120 条），重建时不会退回。
hsk7-2436「真诚地道了歉」原被切成「地道」，已用句子级分词改为 地/道。
可能补语里夹在中间的「不」读轻声（看不见 kàn bu jiàn、找不到 zhǎo bu dào），句首或独用的「不」写本调 bù；
「烟火」指烟花时读 yān huo（官方词表收的是 yānhuǒ「烟和火」义）。这些都写成句子级覆盖。

2026-11-21 普查修正：
- 相邻标点（如 `”，`）曾使带引号句子整句音节错位，已在 `lib/pinyin.py` 修复并加回归测试。
- CEDICT 播种取到少见义项、pypinyin 词组串音（人参加、这种植物）造成的误读，加了 29 条按词覆盖
  （结果 jié、便宜 pián yi、教授 jiào、不了 liǎo、这种 zhǒng、重点 zhòng、当地 dāng、参加 cān 等）。
  共修正 103 条高等记录的拼音字段，中文、分词、词义和音频不变。
- 旧 1–6 级记录中的同类错误经维护者同意一并修正，共 29 条：结果 jiē（8）、便宜 biàn yí（2）、重点 chóng（3）、
  教学 jiāo（1）、参加/参赛/参观 shēn（3）、解决 xiè（1）、处处 chǔ（1）、心脏病 zāng（1）、
  动词「穿着」zhuó（6）、「指着」zháo（2）、不一会儿 儿化未合并（1）。只改拼音字段；
  `data/overrides.json` 补了对应的按词覆盖，6 句「穿着」在 hsk5/hsk6 YAML 中设句子级覆盖。
  旧记录的 `pinyin_numbered` 由 pypinyin 直接生成、不经覆盖层，所以将来若重建 1–6 级，需另行核对这一字段。
- 音频由 CosyVoice 自带 G2P 合成，与拼音字段不是同一来源。

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

2026-11-21 起高等档也计算 `exam_vocab_level_2025`（与 1–6 级同一方法）：5,577 句中 4,513 句为 7–9 合并档，608 句为 6 级，
其余 2–5 级，92 句因含表外字为 `null`。旧记录的估算不变（422 句为高等档）。
npm/PyPI/Hugging Face 未更新版本或远端数据；
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

`docs/advanced-audio-check.json` 是最初 318 句的全量转写；之后各批的筛查结果按批存于本机
`.local/advanced-bulk/*-asr.json`，未纳入版本库。

旧 1–6 级的 `pinyin_numbered` 由 pypinyin 直接生成，约 99 条与带调拼音不一致（如 描述了 liao3、要求 yao1），尚未处理。

下一步：全量听审、未收录词审核、旧 1–6 级数字调拼音与带调拼音对齐，以及发布 v1.2.0。

### v1.2.0 之后：1–6 级拼音复核（2026-11-22）

用 Codex CLI 调 GPT-6.2 Sol 对旧 1–6 级全部 4,354 句做只读拼音审校（`.local/advanced-bulk/tools/pyaudit.py`，约 330 万 token），
共报 212 条，逐句核对后接纳 133 条记录、139 处：多音字（长、种、都、教、场、为、调、系、挨、中、钻、铺等）、
系动词「是」、可能补语中的轻声「不」、必读轻声（学问、队伍、痛快、老婆、徒弟、买卖）、重叠动词后字轻声、
儿化「儿」写 r，以及「一个／每个／那个」的「个」统一为 ge。不接纳的多为与官方词表冲突（心里、合同、困难、好处、味道）
或本项目约定（方位词上/里写本调，「两个」等写 gè）。改动写成句子级覆盖；重叠动词 7 句同一字两读，无法用句子级覆盖表达，重建 1–6 级时需另行处理。
之后又把涉及词条读音的改动逐个对照官方词表扫描页：更正 痛快 tòng kuài、徒弟 tú dì（官方为可轻读，写本调）、事实上 shì shí shang、码头 mǎ tóu（此前统一轻声时按同类推断为 mǎ tou，官方为 mǎ·tóu）。多音字按句意的改动（长、种、教、为等）属语境判断，官方词表只给词条读音，不覆盖具体句子。新指纹在 `data/baselines/v1.2.1.json`（v1.2.1 发布）。变调规则补上比分例外（三比一 yī）。

### 高等拼音：开源库交叉比对（2026-11-22）

不用大模型，改用开源拼音库对照：先在已复核的 1–6 级 32,352 字上测准确度，PinyinJS（`@kensio/pinyinjs` 1.10.9，默认大陆读音）
与现数据一致率最高（98.7%），pinyin-pro 误报最少，g2pW 多音字最强但按台湾读音（和 hàn、期 qí、垃圾 lèsè），只作参考；g2pM 最弱。
三库都不按官方词表区分必读轻声与可轻读，轻声差异不能照搬。再用三库给高等 5,577 句找出与现数据不一致的位置，逐句按语境判断，
词条读音对照官方扫描页（当天 dàngtiān）。共改 214 句、227 处：多音字（名词「地」dì 21 处——`advanced_overrides.json` 把单字「地」统一写 de 所致；
「得」表必须 děi 17 处；长度「长」cháng 15 处；连词「和」hé；弹琴 tán；睡觉 jiào；还钱 huán 等）、声调（种植「种」zhòng 18 处；
任命为/选为 wéi；一场话剧/晚会 chǎng；倒下 dǎo；切菜 qiē；划船 huá；干燥 gān；量体温 liáng 等），以及与 1–6 级约定对齐的轻声
（方位词/趋向补语「上」「里」「来」写本调、学生会 xué shēng、同一个的「个」ge）。改动写成 `hsk7.yaml` 的句子级 `token_pinyin`，
读音变了的词同时更新词义（将 jiāng、中 zhòng 等全局词义不适用的写句子级 `gloss`）；只改 `dist/sentences.json` 中这些记录的拼音与词义，
不整档重建（`--refresh-metadata` 会使 461 句分词漂移）。中文、分词和音频不变。
「谁」官方注 shéi / shuí，两读不分意义和用法，原数据按工具来源混用；现统一写 shéi（全局覆盖 `data/overrides.json`，
1–7 级共 19 句，其中旧 1–6 级 3 句记入 `data/baselines/v1.2.1.json` 的修订记录）。旧 1–6 级 4,354 句也用同法复查：三库不一致的候选（多音字/声调 296 行、轻声 966 处）逐条核对，几乎都是库本身的误读
（局长 cháng、一场误会 chǎng、银行 xíng 等）或与官方词表/项目约定不同的轻声；只改 2 处：切菜 qiē（hsk5-0725）、胡子长了 zhǎng（hsk5-0792），
记入 `data/baselines/v1.2.1.json`。
量词「场」按官方词表统一写 chǎng（词表只收「场 chǎng」，不再按《现代汉语词典》区分事情经过 cháng / 文娱体育 chǎng）：
全局覆盖 `data/overrides.json`，1–7 级共 26 句（一场大雨、一场误会、大病一场等），旧级 7 句记入基线。
