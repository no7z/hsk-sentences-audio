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
        self.entries = {}
        self.entry_ranks = {}
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
                gl = [g for g in glosses.split('/')
                      if g and not g.startswith('CL:') and 'variant of' not in g]
                gloss = '; '.join(gl[:2])
                self.entries.setdefault(simp, []).append((py, gloss))
                # A variant entry can contain substantive-looking glosses after
                # its cross-reference. Prefer the canonical modern entry.
                rank = (int('variant of' in glosses), int(gloss.startswith('used in ')),
                        int(gloss.startswith(('(classical)', '(archaic)', '(old)'))))
                key = (simp, py, gloss)
                self.entry_ranks[key] = min(rank, self.entry_ranks.get(key, rank))
                if simp not in self.pinyin_num:      # 取首个（最常用）义项
                    self.pinyin_num[simp] = py
                    gl = [g for g in glosses.split('/')
                          if g and not g.startswith('CL:') and 'variant of' not in g]
                    self.gloss[simp] = '; '.join(gl[:2])

    def gloss_for(self, word, toned_pinyin):
        """Prefer a substantive entry with the actual contextual reading.

        Modern CEDICT places many variant-only and surname entries first.
        The legacy first-entry maps remain available to existing consumers.
        """
        from lib.pinyin import cedict_word_toned
        entries = [(py, gloss) for py, gloss in self.entries.get(word, []) if gloss]
        reading = toned_pinyin.replace(' ', '').lower()
        matching = [(py, gloss) for py, gloss in entries
                    if ''.join(cedict_word_toned(py)).lower() == reading]
        choices = matching or entries
        choices.sort(key=lambda e: (e[0][0].isupper(),
                                    self.entry_ranks.get((word, e[0], e[1]), (0, 0, 0)),
                                    e[1].startswith(('surname ', 'abbr. for '))))
        return choices[0][1] if choices else ''

    def has(self, word):
        return word in self.vocab
