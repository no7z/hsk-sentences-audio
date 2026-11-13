# -*- coding: utf-8 -*-
"""Level of a sentence under the 2025 HSK examination syllabus.

The sentences are authored against GF0025-2021. The HSK 3.0 exam that starts on
13 December 2026 is set from a different document, the 2025 syllabus
(《中文水平考试HSK考试大纲》), which places many common words differently:
用 and 先 are level 1 in GF0025-2021 and level 3 in the syllabus. This gives the
exam's view of each sentence next to the authored level, so an app can filter
by either.

The syllabus word and character lists come from hsk30 (MIT,
https://pypi.org/project/hsk30/). It is optional: without it the field is null.
"""
from functools import lru_cache

try:
    import hsk30
except ImportError:  # pip install hsk30
    hsk30 = None


@lru_cache(maxsize=1)
def _tables():
    return hsk30.words("2025"), hsk30.characters("2025")


def exam_level(words):
    """Hardest level among a sentence's words in the 2025 syllabus.

    A word the syllabus does not list counts at its hardest listed character.
    Returns 1-6, 7 for the 7-9 band, or None when nothing can be graded or
    hsk30 is not installed.
    """
    if hsk30 is None:
        return None
    word_level, char_level = _tables()
    levels = []
    for w in words:
        if w in word_level:
            levels.append(word_level[w])
        else:
            chars = [char_level[c] for c in w if c in char_level]
            if chars:
                levels.append(max(chars))
    return max(levels) if levels else None
