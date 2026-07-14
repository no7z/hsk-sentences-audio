import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsk_sentences_audio import audio_url, iter_sentences, load_sentences  # noqa: E402


class LoaderTest(unittest.TestCase):
    def test_loads_canonical_dataset(self) -> None:
        records = load_sentences()
        self.assertEqual(len(records), 4354)
        self.assertEqual(records[0]["id"], "hsk1-0001")

    def test_filters_and_resolves_audio(self) -> None:
        sentence = next(iter_sentences(level=6))
        self.assertEqual(sentence["hsk_level"], 6)
        self.assertTrue(
            audio_url(sentence, speed="slow", base_url="https://cdn.example/data/").startswith(
                "https://cdn.example/data/audio/hsk6-"
            )
        )


if __name__ == "__main__":
    unittest.main()
