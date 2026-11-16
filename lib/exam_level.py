# -*- coding: utf-8 -*-
"""Estimated vocabulary level against the 2025 HSK examination syllabus.

The sentences are authored against GF0025-2021. The HSK 3.0 exam that starts on
13 December 2026 is set from a different document, the 2025 syllabus
(《中文水平考试HSK考试大纲》), which places many common words differently:
用 and 先 are level 1 in GF0025-2021 and level 3 in the syllabus. This gives the
vocabulary estimate next to the authored level. This is not an official
sentence grade: grammar, senses and parts of speech are not evaluated.

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

    Listed words use their lowest listed level (no sense disambiguation).
    Unlisted words fall back to recognition-character levels. Unknown Han
    characters make the entire result None rather than being silently ignored.
    Punctuation and non-Han text do not contribute. Returns 1-6, 7 for the
    combined 7-9 band, or None if unavailable or not fully gradeable.
    """
    if hsk30 is None:
        return None
    word_level, char_level = _tables()
    levels = []
    for w in words:
        if w in word_level:
            levels.append(word_level[w])
        else:
            hanzi = [c for c in w if _is_han(c)]
            if any(c not in char_level for c in hanzi):
                return None
            chars = [char_level[c] for c in hanzi]
            if chars:
                levels.append(max(chars))
    return max(levels) if levels else None


def _is_han(char):
    code = ord(char)
    return (0x3400 <= code <= 0x4DBF or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF or 0x20000 <= code <= 0x2FA1F
            or 0x30000 <= code <= 0x3347F or char == "〇")
