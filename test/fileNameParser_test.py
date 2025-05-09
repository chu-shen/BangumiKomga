import unittest
from tools.fileNameParser import FileNamePaser


class TestFileNameParser(unittest.TestCase):
    def setUp(self):
        self.parser = FileNamePaser()

    def test_episode_extraction(self):
        self.parser.parse("[21世紀小福星][藤子·F·不二雄][青文][浪速之虎][4完]")
        self.assertEqual(self.parser.parts.get('episode'), 4)

    def test_multiple_patterns(self):
        test_str = "[人形之国 全彩版][贰瓶勉][Vol.01-Vol.09][官方简中]"
        self.parser.parse(test_str)
        self.assertEqual(self.parser.parts['title'], "人形之国 全彩版")
        self.assertEqual(self.parser.parts['episode'], 9)
        self.assertEqual(self.parser.parts['author'], "贰瓶勉")
        self.assertEqual(self.parser.parts['excess'], "官方简中")

    def test_multiple_patterns_with_symbols(self):
        test_str = "[新世纪福音战士 碇真嗣育成计划][高橋脩×GAINAX×khara][台湾角川][18完]"
        self.parser.parse(test_str)
        self.assertEqual(self.parser.parts['title'], "新世纪福音战士 碇真嗣育成计划")
        self.assertEqual(self.parser.parts['episode'], 18)
        self.assertEqual(self.parser.parts['author'], "高橋脩×GAINAX×khara")
        self.assertEqual(self.parser.parts['publisher'], "台湾角川")
        test_str = "[ツガノガク] [涼宮春日的憂鬱] [台灣角川] [1-20完]"
        self.parser.parse(test_str)
        self.assertEqual(self.parser.parts['title'], "涼宮春日的憂鬱")
        self.assertEqual(self.parser.parts['episode'], 20)
        self.assertEqual(self.parser.parts['author'], "ツガノガク")
        self.assertEqual(self.parser.parts['publisher'], "台灣角川")
        test_str = "河门——不存在的神圣（完全漫画版）"
        self.parser.parse(test_str)
        self.assertEqual(self.parser.parts['title'], "河门——不存在的神圣")
        self.assertEqual(self.parser.parts['excess'], "完全漫画版")
        test_str = "天堂里的异乡人(1993)"
        self.parser.parse(test_str)
        self.assertEqual(self.parser.parts['title'], "天堂里的异乡人")
        self.assertEqual(self.parser.parts['year'], 1993)

    def test_multiple_patterns_oneshot(self):
        test_str = "[新海诚×本桥翠][言叶之庭][Vol.01全][四川美术]"
        self.parser.parse(test_str)
        self.assertEqual(self.parser.parts['episode'], 1)
        self.assertEqual(self.parser.parts['author'], "新海诚×本桥翠")
        self.assertEqual(self.parser.parts['title'], "言叶之庭")
        self.assertEqual(self.parser.parts['publisher'], "四川美术")

    def test_boolean_type(self):
        self.parser.parse("哆啦A梦大长篇(藤子·F·不二雄)")
        self.assertTrue(self.parser.parts.get('translated', False))
        self.assertTrue(self.parser.parts['title'], "哆啦A梦大长篇")
        self.assertTrue(self.parser.parts['year'], "藤子·F·不二雄")
        self.parser.parse("[哥布林杀手 外传：锷鸣的太刀][个人汉化]")
        self.assertTrue(self.parser.parts.get('translated', True))
        self.assertTrue(self.parser.parts['title'], "哥布林杀手 外传：锷鸣的太刀")

    def test_title_extraction(self):
        self.parser.parse("[まめおじたん] 生活在拔作一样的岛上我该怎么办才好 [1-2卷]")
        self.assertEqual(self.parser.parts['title'], "生活在拔作一样的岛上我该怎么办才好")
        self.assertEqual(self.parser.parts['author'], "まめおじたん")

    def test_invalid_input(self):
        self.parser.parse("天敌抗战记VERSUS")
        self.assertEqual(self.parser.parts["title"], "天敌抗战记VERSUS")


if __name__ == '__main__':
    unittest.main()
