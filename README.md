# chinese-sentences-audio

> 中文分级句子数据集：句子 + 拼音 + 英文翻译 + 逐词词义 + 语法点标注 + 常速/慢速音频，依官方 HSK 3.0 标准分级，开箱即用的 JSON + MP3。

为中文学习类应用提供现成的数据层。每个句子都是一条自包含的结构化记录，配套双速音频，可直接用于闪卡、跟读、听力、SRS 等场景。

## 当前规模

| 等级 | 句子数 | 词表覆盖 | 超纲词 |
|---|---|---|---|
| HSK 1 | 281 | 94%（480/506 词） | 0 |
| HSK 2 | 538 | 100%（750/750 词） | 0 |
| **合计** | **819 句** | — | **0** |

配套音频 1638 个 MP3（每句常速 + 慢速各一）。

分级依据《国际中文教育中文水平等级标准》（GF0025-2021，即 "HSK 3.0"）：每一级的句子**只使用该级及以下的词汇**（零超纲），并系统性覆盖该级词表——两项指标均可用仓库内的校验器复核，不是口头声明。

## 数据长什么样

`dist/sentences.json` 中的一条记录：

```json
{
  "id": "hsk1-0002",
  "hsk_level": 1,
  "topic": "greetings",
  "sentence_type": "statement",
  "chinese": "你好，很高兴认识你。",
  "traditional": "你好，很高興認識你。",
  "pinyin": "nǐ hǎo hěn gāo xìng rèn shi nǐ",
  "pinyin_numbered": "ni3 hao3 hen3 gao1 xing4 ren4 shi5 ni3",
  "translation": { "en": "Hello, nice to meet you." },
  "tokens": [
    { "word": "很",   "pinyin": "hěn",     "gloss_en": "very; quite" },
    { "word": "高兴", "pinyin": "gāo xìng", "gloss_en": "happy; glad" },
    { "word": "认识", "pinyin": "rèn shi",  "gloss_en": "to know; to recognize" }
  ],
  "grammar_tags": ["1-09"],
  "audio": { "normal": "audio/hsk1-0002.mp3", "slow": "audio/hsk1-0002_slow.mp3" },
  "audio_meta": { "engine": "cosyvoice2-0.5B", "voice": "zh-female-studio",
                  "license": "Apache-2.0", "sample_rate": 24000 }
}
```

字段说明：

- **pinyin / tokens.pinyin** — 处理过轻声（认识 = rèn **shi**）、上下文多音字（要 = yào）、儿化（哪儿 = nǎr）；整句拼音与逐词拼音保证一致
- **topic** — 18 个主题（问候礼貌 / 家庭 / 时间日期 / 饮食 / 出行交通 / 健康身体…）
- **sentence_type** — 陈述句 / 疑问句 / 祈使句
- **grammar_tags** — 官方语法点编号（如 `"1-09"` =【一09】程度副词），对照表见 `data/grammar_points.json`（含官方分类、等级、例句）
- **audio** — 常速 + 慢速 MP3，本地合成（CosyVoice2，Apache-2.0），已做去杂音后处理，可随数据集自由再分发

## 直接使用

- **浏览数据**：双击打开 `dist/index.html`——离线可用，无需起服务。支持搜索与四维联动筛选（等级 / 主题 / 句型 / 语法点，计数实时联动），点击播放音频
- **接入开发**：打开 `dist/setup.html`——一键导出 SQL（SQLite/PostgreSQL/MySQL）、CSV、Anki 导入文件；复制即用的 Swift / TypeScript / Kotlin 数据模型；按目标（iOS SRS 应用 / FastAPI 后端 / React 练习页）生成携带完整 schema 说明的 LLM 提示词
- **程序读取**：直接消费 `dist/sentences.json` + `dist/audio/`

## 从源码构建

```bash
# 1. 文本管线依赖
pip install -r requirements.txt

# 2. 下载 CC-CEDICT 词典与官方 HSK 词表/语法点原文
python scripts/download_cedict.py
python scripts/download_hsk.py

# 3. 只出文本数据（校对拼音/分词，无需 TTS）
python build.py --level 1 --no-audio

# 4. 分级校验：超纲词 + 词表覆盖率
python scripts/hsk_validate.py --level 1

# 5. 音频合成（需另装 CosyVoice，设 COSYVOICE_REPO 后）
python scripts/make_reference.py     # 生成参考音色（一次性）
python build.py --level 1            # 全量构建（断点续跑）
```

有 NVIDIA 显卡的机器可以只负责音频合成（约 4-8 倍于 CPU），见 [docs/WINDOWS-GPU.md](docs/WINDOWS-GPU.md)：`scripts/synth_audio.py` 只读 `dist/sentences.json` 补齐缺失音频，与文本管线完全解耦。

## 质量机制

- **分级校验**（`scripts/hsk_validate.py`）：按官方词表逐词检查——containment（报出任何高于目标级的词，目标零超纲）与 coverage（目标级词表覆盖率），"符合 HSK X 级"是能跑出数字的属性
- **语法点注册表**（`data/grammar_points.json`）：官方一、二级全部 129 个语法点（编号/等级/分类/例句），其中 70 个带自动检测规则；规则由 `scripts/test_grammar_rules.py` 的回归测试保护（历史误报均固化为负例）
- **拼音**：pypinyin 提供句级上下文 + CC-CEDICT 批量播种轻声/儿化修正 + 人工 override 层（`data/overrides.json`），文字与音频同源
- **分词**：jieba（HMM 关闭）+ HSK 全级词表回拆（自动拆开"坐地铁/很漂亮"类粘连）+ 例外表
- **音频**：CosyVoice2-0.5B 本地合成，录音棚女声音色，开头瞬态裁除 + 淡入；合成语音（synthetic voice），下游使用建议照惯例标注
- **审核流**：构建时自动标红多音字/未收录词（`dist/review_flags.txt`）→ 人工确认 → 修正沉淀进 `data/overrides.json`，一次生效永久复用

## 新增句子

编辑 `data/sentences/hsk<level>.yaml`，每句只需三个字段：

```yaml
- { chinese: "你好，很高兴认识你。", en: "Hello, nice to meet you.", grammar: ["很 + adj"] }
```

拼音、繁体、分词、词义、主题、句型、语法点、音频全部由管线自动生成；跑一遍校验器确认零超纲即可。

## 许可

- **代码**：MIT（见 `LICENSE`）
- **数据集 `dist/`**：CC-BY-SA 4.0（词义与逐词拼音含 CC-CEDICT 衍生内容；音频由 Apache-2.0 的 CosyVoice2 合成）
- 完整来源与署名见 [ATTRIBUTION.md](ATTRIBUTION.md)
