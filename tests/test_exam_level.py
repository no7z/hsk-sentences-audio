import unittest
from unittest.mock import patch

from lib import exam_level as exam
from scripts.enrich_exam_levels import enrich_records


class ExamLevelTest(unittest.TestCase):
    def setUp(self):
        self.package = patch.object(exam, "hsk30", object())
        self.package.start()
        self.tables = patch.object(exam, "_tables", return_value=(
            {"我": 1, "先": 3, "黑": 5, "钻研": 7},
            {"我": 1, "先": 1, "黑": 2, "回": 2, "家": 1},
        ))
        self.tables.start()
        self.addCleanup(self.package.stop)
        self.addCleanup(self.tables.stop)

    def test_word_level_precedes_character_level(self):
        self.assertEqual(exam.exam_level(["我", "先", "黑"]), 5)

    def test_unlisted_compound_uses_hardest_character(self):
        self.assertEqual(exam.exam_level(["回家", "！"]), 2)

    def test_unknown_hanzi_must_not_be_ignored(self):
        for unknown in ["龘", "家龘", "𠀀", "〇"]:
            with self.subTest(unknown=unknown):
                self.assertIsNone(exam.exam_level(["我", unknown]))

    def test_empty_punctuation_and_latin_are_ungraded(self):
        for tokens in [[], ["。", "123", "ABC"]]:
            self.assertIsNone(exam.exam_level(tokens))
        self.assertEqual(exam.exam_level(["我", "。", "ABC"]), 1)

    def test_high_band_is_not_an_individual_seventh_level(self):
        self.assertEqual(exam.exam_level(["钻研"]), 7)

    def test_missing_optional_dependency(self):
        with patch.object(exam, "hsk30", None):
            self.assertIsNone(exam.exam_level(["我"]))

    def test_backfill_preserves_existing_data_and_input(self):
        record = {"id": "hsk1-0001", "hsk_level": 1, "tokens": [{"word": "先"}],
                  "audio": {"normal": "audio/hsk1-0001.mp3"}}
        result = enrich_records([record])[0]
        self.assertEqual(result["exam_vocab_level_2025"], 3)
        self.assertNotIn("exam_vocab_level_2025", record)
        self.assertEqual({k: v for k, v in result.items() if k != "exam_vocab_level_2025"}, record)


if __name__ == "__main__":
    unittest.main()
