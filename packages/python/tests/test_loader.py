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

    def test_exam_filter_is_independent_of_authored_level(self) -> None:
        records = load_sentences()
        self.assertTrue(all(type(r["exam_vocab_level_2025"]) is int and 1 <= r["exam_vocab_level_2025"] <= 7 for r in records))
        example = next(r for r in records if r["hsk_level"] != r["exam_vocab_level_2025"])
        result = list(iter_sentences(level=example["hsk_level"], exam_vocab_level=example["exam_vocab_level_2025"]))
        self.assertIn(example, result)
        self.assertTrue(all(r["hsk_level"] == example["hsk_level"] and r["exam_vocab_level_2025"] == example["exam_vocab_level_2025"] for r in result))


if __name__ == "__main__":
    unittest.main()
