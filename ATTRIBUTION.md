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

## 关于音频

- 音频由 CosyVoice2-0.5B 在本地合成，**合成语音**（synthetic voice）；输入文本为本项目自有内容。
- CosyVoice 模型语音本身的知识产权归其作者所有；本项目依 Apache-2.0 再分发合成输出。
- 使用者在下游产品中使用本音频时，建议按惯例标注“合成语音”。

## 数据集许可

- `dist/sentences.json` 中源自 CC-CEDICT 的字段（词义、逐词拼音）受 CC-BY-SA 4.0 约束。
- 句子文本与英文翻译为本项目自有。
- 为简化合规，整个 `dist/` 数据集以 **CC-BY-SA 4.0** 发布。
