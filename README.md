# chinese-sentences-audio

> 面向语言学习 App 开发者的中文分级句子数据层 —— 句子 + 拼音 + 多语翻译 + 逐词词义 + 原生音质音频 + HSK 分级，开箱即用 JSON。

做中文学习 App 的开发者，目前要么付费买句库/音频 API，要么自己拼 Tatoeba（无分级、音频零散）、拆 Anki 卡包（格式不友好、版权不清）。**没有一个像 [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) 之于健身 App 那样、开箱即用的中文句子数据层。** 这个项目补上这个缺口，而且**许可全程干净**（音频用开源 CosyVoice2 本地合成，可随数据集一起分发）。

**分级依据官方标准**：《国际中文教育中文水平等级标准》(GF0025-2021，即"HSK 3.0"，三等九级)。每个批次对目标等级做**可校验的**词表 containment（零超纲）与 coverage（覆盖率）检查——不是"大致像 HSK"，而是拿官方词表逐词卡。当前 **HSK 一级**：281 句，覆盖一级 506 词的 **94%**，**零超纲**。

## 数据长什么样

每条记录（`dist/sentences.json`）：

```json
{
  "id": "hsk1-0001",
  "hsk_level": 1,
  "chinese": "你好，很高兴认识你。",
  "traditional": "你好，很高興認識你。",
  "pinyin": "nǐ hǎo hěn gāo xìng rèn shi nǐ",
  "pinyin_numbered": "ni3 hao3 hen3 gao1 xing4 ren4 shi5 ni3",
  "translation": { "en": "Hello, nice to meet you." },
  "tokens": [
    { "word": "你好", "pinyin": "nǐ hǎo", "gloss_en": "hello" },
    { "word": "很",   "pinyin": "hěn",    "gloss_en": "very" },
    { "word": "高兴", "pinyin": "gāo xìng", "gloss_en": "happy; glad" },
    { "word": "认识", "pinyin": "rèn shi", "gloss_en": "to know; to be acquainted with" },
    { "word": "你",   "pinyin": "nǐ",     "gloss_en": "you" }
  ],
  "grammar_points": ["很 + adj"],
  "audio": { "normal": "audio/hsk1-0001.mp3", "slow": "audio/hsk1-0001_slow.mp3" },
  "audio_meta": { "engine": "cosyvoice2-0.5B", "voice": "zh-female-studio", "license": "Apache-2.0", "sample_rate": 24000 }
}
```

配套音频：`dist/audio/<id>.mp3`（常速）与 `<id>_slow.mp3`（慢速，初学者跟读）。

## 技术栈

| 环节 | 方案 | 许可 |
|---|---|---|
| TTS 引擎 | CosyVoice2-0.5B（本地 CPU，~5s/句） | Apache-2.0 |
| 音色 | 零样本 + 录音棚中文女参考音频 | Apache-2.0 |
| 音频后处理 | 裁开头 70ms + 30ms 淡入（去 onset 杂音） | — |
| 拼音 | pypinyin + CC-CEDICT 播种 override（修轻声/多音字/儿化） | MIT / CC-BY-SA |
| 繁体 | OpenCC | Apache-2.0 |
| 分词 | jieba (HMM off) + 例外表 | MIT |
| 词义 | CC-CEDICT | CC-BY-SA |
| 分级校验 | 对官方 HSK 词表做 containment + coverage | — |
| 审核 | 自动标红多音字/未收录词 → 人工秒批 → 沉淀 overrides | — |

拼音的轻声（认识 = rèn **shi**）、多音字上下文（要 = yào）、儿化（哪儿 = nǎr）都做了处理，细节见 `lib/pinyin.py`。

## 快速开始

```bash
# 1. 文本管线依赖
pip install -r requirements.txt

# 2. 下载 CC-CEDICT 词典 + HSK 词表
python scripts/download_cedict.py
python scripts/download_hsk.py

# 3. 只出文本数据（快速校对拼音，无需 TTS）
python build.py --level 1 --no-audio

# 4. 校验分级：对官方 HSK 一级词表检查超纲/覆盖率
python scripts/hsk_validate.py --level 1

# 5. 装 CosyVoice（Apache-2.0）后生成参考音色 + 全量构建（含音频）
#    参见 https://github.com/FunAudioLLM/CosyVoice ，设置 COSYVOICE_REPO 后：
python scripts/make_reference.py
python build.py --level 1
```

生成结果在 `dist/`。浏览器预览：打开 `web/index.html`（按级别/语法点筛选、点击播放音频）。

## 分级校验（可复验的"符合 HSK"）

`scripts/hsk_validate.py` 拿官方 HSK 词表逐词检查句子集：
- **Containment（超纲）**：用等级感知的分词，报出任何高于目标级的词；目标是**零超纲**。
- **Coverage（覆盖）**：报出目标级词表被句子覆盖的比例。

这样"符合 HSK X 级"是一个能跑出数字的属性，而不是口头声明。

## 校对流程

`build.py` 会输出 `dist/review_flags.txt`，标出含多音字或未收录词的 token 供人工快速确认。确认后的修正写入 `data/overrides.json`（多音字读音 / 分词拆分 / 逐词拼音 / 词义），一次沉淀、永久复用。

## 贡献

新增句子只需编辑 `data/sentences/hsk<level>.yaml`，填 `chinese` / `en` / `grammar` 三个字段，其余（拼音、繁体、分词、词义、音频）由管线自动生成。

## 许可

- **代码**：MIT（见 `LICENSE`）
- **数据集 `dist/`**：CC-BY-SA 4.0（含 CC-CEDICT 衍生字段 + CosyVoice2 合成音频）
- 详见 `ATTRIBUTION.md`
