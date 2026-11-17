import tempfile
from pathlib import Path
import unittest

from lib.cedict import Cedict


class CedictReadingTest(unittest.TestCase):
    def test_variant_with_extra_glosses_does_not_override_canonical_word(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'cedict.txt'
            p.write_text('佈 布 [bu4] /variant of 布[bu4]/to announce/to spread/\n'
                         '布 布 [bu4] /cloth/to declare/\n'
                         '傢 家 [jia1] /used in 傢伙|家伙[jia1 huo5]/\n'
                         '家 家 [jia1] /home/family/\n', encoding='utf-8')
            dictionary = Cedict(p)
            self.assertEqual(dictionary.gloss_for('布', 'bù'), 'cloth; to declare')
            self.assertEqual(dictionary.gloss_for('家', 'jiā'), 'home; family')
            self.assertEqual(dictionary.gloss['布'], 'to announce; to spread')

    def test_variant_and_proper_name_do_not_hide_substantive_gloss(self):
        try:
            import pypinyin  # noqa: F401
        except ImportError:
            self.skipTest("Text pipeline dependencies are optional in loader-only CI")
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "cedict.txt"
            p.write_text("㕁 却 [que4] /old variant of 卻|却[que4]/\n"
                         "卻 却 [que4] /but/yet/\n"
                         "尚 尚 [Shang4] /surname Shang/\n"
                         "尚 尚 [shang4] /still/yet/\n"
                         "為 为 [wei2] /to become/to be/\n"
                         "為 为 [wei4] /for/because of/\n", encoding="utf-8")
            dictionary = Cedict(p)
            self.assertEqual(dictionary.gloss_for("却", "què"), "but; yet")
            self.assertEqual(dictionary.gloss_for("尚", "shàng"), "still; yet")
            self.assertEqual(dictionary.gloss_for("为", "wèi"), "for; because of")
            self.assertEqual(dictionary.gloss_for("为", "wéi"), "to become; to be")
            self.assertEqual(dictionary.gloss["尚"], "surname Shang")  # legacy API preserved


if __name__ == "__main__":
    unittest.main()
