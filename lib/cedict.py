# -*- coding: utf-8 -*-
"""CC-CEDICT 加载器（CC-BY-SA）。提供词表、逐词标准拼音（含轻声/儿化）、英文释义。"""
import re
from pathlib import Path

_LINE = re.compile(r'^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/\s*$')


class Cedict:
    def __init__(self, path):
        self.vocab = set()
        self.pinyin_num = {}   # 简体词 -> 数字调号拼音，如 "ren4 shi5"
        self.gloss = {}        # 简体词 -> 前若干英文释义
        self._load(Path(path))

    def _load(self, path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                m = _LINE.match(line)
                if not m:
                    continue
                _trad, simp, py, glosses = m.groups()
                self.vocab.add(simp)
                if simp not in self.pinyin_num:      # 取首个（最常用）义项
                    self.pinyin_num[simp] = py
                    gl = [g for g in glosses.split('/')
                          if g and not g.startswith('CL:') and 'variant of' not in g]
                    self.gloss[simp] = '; '.join(gl[:2])

    def has(self, word):
        return word in self.vocab
