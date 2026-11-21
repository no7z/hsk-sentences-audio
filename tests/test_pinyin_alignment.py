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



class YiBuSandhiTest(unittest.TestCase):
    def run_case(self, text, words, pys):
        return P.apply_yi_bu_sandhi(text, words, pys)

    def test_bu_before_fourth_tone_and_a_bu_a(self):
        self.assertEqual(self.run_case('好久不见。', ['好久', '不见', '。'], ['hǎo jiǔ', 'bù jiàn', ''])[1], 'bú jiàn')
        self.assertEqual(self.run_case('不行。', ['不行', '。'], ['bù xíng', ''])[0], 'bù xíng')
        self.assertEqual(self.run_case('能不能来？', ['能', '不能', '来', '？'], ['néng', 'bù néng', 'lái', ''])[1], 'bu néng')
        self.assertEqual(self.run_case('它一动不动。', ['它', '一动不动', '。'], ['tā', 'yī dòng bù dòng', ''])[1], 'yí dòng bú dòng')

    def test_yi_cardinal_ordinal_and_reduplication(self):
        got = self.run_case('他是第一名，一个人看一看。', ['他', '是', '第一', '名', '，', '一个', '人', '看', '一', '看', '。'],
                            ['tā', 'shì', 'dì yī', 'míng', '', 'yī ge', 'rén', 'kàn', 'yī', 'kàn', ''])
        self.assertEqual((got[2], got[5], got[8]), ('dì yī', 'yí ge', 'yi'))
        got = self.run_case('一月一日统一起来。', ['一月', '一日', '统一', '起来', '。'], ['yī yuè', 'yī rì', 'tǒng yī', 'qǐ lái', ''])
        self.assertEqual(got[:3], ['yī yuè', 'yī rì', 'tǒng yī'])
        self.assertEqual(self.run_case('一起走。', ['一起', '走', '。'], ['yī qǐ', 'zǒu', ''])[0], 'yì qǐ')


if __name__ == '__main__':
    unittest.main()
