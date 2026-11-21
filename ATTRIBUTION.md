# 数据与依赖来源 / Attribution

本项目的**代码**以 MIT 许可发布（见 `LICENSE`）。生成的**数据集**（`dist/`）由下列组件产生，各自的许可与署名如下：

| 组件 | 用途 | 许可 | 署名要求 |
|---|---|---|---|
| [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) | 词义、逐词标准拼音 | CC-BY-SA 4.0 | 需署名，衍生数据同以 CC-BY-SA 分享 |
| [CosyVoice2-0.5B](https://github.com/FunAudioLLM/CosyVoice) | 音频合成（TTS） | Apache-2.0 | 保留版权声明 |
| [pypinyin](https://github.com/mozillazg/python-pinyin) | 拼音注音 | MIT | — |
| [jieba](https://github.com/fxsjy/jieba) | 分词 | MIT | — |
| [OpenCC](https://github.com/BYVoid/OpenCC) | 简→繁转换 | Apache-2.0 | — |
| [complete-hsk-vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary) | HSK 分级词表（用于分级校验，非直接入库） | MIT | — |

## 关于 HSK 分级

分级依据官方《国际中文教育中文水平等级标准》(GF0025-2021)。校验用的机读词表来自社区数字化项目 complete-hsk-vocabulary，与官方口径约有 ~1% 出入；关键级别建议对照官方查询系统（[chinesetest.cn](https://admin.chinesetest.cn/standardsAction.do?means=standardInfo)）复核。

### 原标准高等档词表快照

`data/standards/gf0025-2021-7-9.txt` is a pinned transcription from
[Mani / krmanik, HSK-3.0](https://github.com/krmanik/HSK-3.0/blob/5a7a6111fe4ff0d5fa98f06ffb440af10627a927/New%20HSK%20(2021)/HSK%20List/HSK%207-9.txt),
credited as **CC-BY-SA 4.0** in the upstream
[License.md](https://github.com/krmanik/HSK-3.0/blob/5a7a6111fe4ff0d5fa98f06ffb440af10627a927/License.md).
This snapshot retains 5,636 rows, including repeated spellings. Its provenance,
checksum and limitations are recorded in the adjacent `.source.json`.
It is a community transcription, not an official digital edition. Coverage
counts distinct spellings, not separately validated readings or senses.
The normative reference is the Ministry of Education's
[GF0025-2021 PDF](https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202103/W020210329527301787356.pdf),
section 6.7 (printed pages 102–169).

## 关于音频

- 音频由 CosyVoice2-0.5B 在本地合成，**合成语音**（synthetic voice）；输入文本为本项目自有内容。
- CosyVoice 模型语音本身的知识产权归其作者所有；本项目依 Apache-2.0 再分发合成输出。
- 使用者在下游产品中使用本音频时，建议按惯例标注“合成语音”。

## 数据集许可

- `dist/sentences.json` 中源自 CC-CEDICT 的字段（词义、逐词拼音）受 CC-BY-SA 4.0 约束。
- 句子文本与英文翻译为本项目自有。
- 为简化合规，整个 `dist/` 数据集以 **CC-BY-SA 4.0** 发布。

## 新增考试词汇估算 / Exam vocabulary estimates

`exam_vocab_level_2025` uses the 2025 HSK examination syllabus via the third-party
[hsk30](https://github.com/harukicoder/hsk30) package, maintained by Alvaro Serrano.
This is not an official package or an official sentence grade. The 2021 authored
levels remain unchanged. See `dist/exam_vocab_metadata.json` for the reviewed
package version, table hashes, method, limitations and the original-data fingerprint.
The original syllabus is published by 中外语言交流合作中心 and linked from
[中文考试服务网](https://www.chinesetest.cn/Development?lang=cn).

The hsk30 software licence is retained below; it does not establish official
endorsement or ownership of the underlying official syllabus.

```text
MIT License

Copyright (c) 2026 Alvaro Serrano

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
