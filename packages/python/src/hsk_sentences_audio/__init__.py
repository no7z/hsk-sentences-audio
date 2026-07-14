"""Dependency-free access to the hsk-sentences-audio dataset."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
import json
from typing import Any, Iterator, Literal, Optional
from urllib.parse import urljoin

__version__ = "1.0.0"
DATASET_LICENSE = "CC-BY-SA-4.0"
DEFAULT_AUDIO_BASE_URL = "https://raw.githubusercontent.com/no7z/hsk-sentences-audio/main/dist/"

Sentence = dict[str, Any]
AudioSpeed = Literal["normal", "slow"]


@lru_cache(maxsize=1)
def load_sentences() -> list[Sentence]:
    """Load and cache all 4,354 packaged sentence records."""
    resource = files("hsk_sentences_audio").joinpath("data", "sentences.json")
    with resource.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_sentences(
    *,
    level: Optional[int] = None,
    topic: Optional[str] = None,
    sentence_type: Optional[str] = None,
) -> Iterator[Sentence]:
    """Iterate over records matching optional HSK level/topic/type filters."""
    for sentence in load_sentences():
        if level is not None and sentence["hsk_level"] != level:
            continue
        if topic is not None and sentence["topic"] != topic:
            continue
        if sentence_type is not None and sentence["sentence_type"] != sentence_type:
            continue
        yield sentence


def audio_url(
    sentence: Sentence,
    *,
    speed: AudioSpeed = "normal",
    base_url: str = DEFAULT_AUDIO_BASE_URL,
) -> str:
    """Resolve a sentence's normal or slow MP3 path against an asset base URL."""
    if speed not in ("normal", "slow"):
        raise ValueError(f"Unknown audio speed: {speed}")
    try:
        relative = sentence["audio"][speed]
    except (KeyError, TypeError) as error:
        raise ValueError(f"Sentence {sentence.get('id', '(unknown)')} has no {speed} audio path") from error
    return urljoin(base_url.rstrip("/") + "/", relative)


__all__ = [
    "AudioSpeed",
    "DATASET_LICENSE",
    "DEFAULT_AUDIO_BASE_URL",
    "Sentence",
    "audio_url",
    "iter_sentences",
    "load_sentences",
]
