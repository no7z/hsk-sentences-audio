import unittest

from lib import pinyin as P


class PinyinAlignmentTest(unittest.TestCase):
    def test_adjacent_punctuation_does_not_shift_syllables(self):
        # lazy_pinyin returns "”，" as one element; alignment must still be per character.
        text = '古人说“三人行，必有我师”，我们要学习。'
        tokens = ['古人', '说', '“', '三人行', '，', '必', '有', '我', '师', '”', '，', '我们', '要', '学习', '。']
        got = P.token_pinyin(text, tokens, P.sentence_char_pinyin(text))
        self.assertEqual(got[tokens.index('我们')], 'wǒ men')
        self.assertEqual(got[tokens.index('学习')], 'xué xí')
        self.assertEqual(got[-1], '')

    def test_every_han_character_gets_one_syllable(self):
        text = '他说：“好！”然后走了。'
        cm = P.sentence_char_pinyin(text)
        self.assertEqual(sorted(cm), [i for i, c in enumerate(text) if '一' <= c <= '鿿'])
        self.assertEqual(cm[text.index('然')], 'rán')


if __name__ == '__main__':
    unittest.main()
