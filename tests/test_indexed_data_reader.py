from bangumi_archive.indexed_jsonlines_read import IndexedDataReader
from unittest.mock import patch, MagicMock, mock_open
import pickle
import json
import os
import unittest

# @unittest.skip("临时跳过测试")


class TestIndexedDataReader(unittest.TestCase):
    def setUp(self):
        """准备测试数据及文件"""

        self.sample_relation_data = [{"subject_id": 8, "relation_type": 1004, "related_subject_id": 1081, "order": 0},
                                     {"subject_id": 8, "relation_type": 3001,
                                         "related_subject_id": 3219, "order": 6},
                                     {"subject_id": 8, "relation_type": 3004,
                                         "related_subject_id": 8813, "order": 2},
                                     {"subject_id": 8, "relation_type": 3003,
                                      "related_subject_id": 8816, "order": 1},
                                     {"subject_id": 8, "relation_type": 3003,
                                      "related_subject_id": 8817, "order": 2},
                                     {"subject_id": 8, "relation_type": 3099, "related_subject_id": 8819, "order": 15}]
        self.sample_subject_data = [
            {"id": 328150, "type": 1, "name": "ニューノーマル", "name_cn": "新常态", "infobox": "{{Infobox animanga/Manga\r\n|中文名= 新常态\r\n|别名={\r\n[你和我的嘴唇]\r\n[未来的恋爱必须戴口罩]\r\n[New Normal]\r\n}\r\n|出版社= ファンギルド\r\n|价格= \r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2021-07-19\r\n|册数= \r\n|页数= \r\n|话数= \r\n|ISBN= \r\n|其他= \r\n|作者= 相原瑛人\r\n|开始= 2020-12-18\r\n}}", "platform": 1001, "summary": "你的口罩下是住在我心里的那张脸\r\n\r\n「僕たちが生まれる少し前、ひとつの感染症が世界を変えた」――マスクで口元を隠すことが当たり前の日常となった近未来。世界流行\u003cパンデミック\u003e前の時代に密かに思いを馳せる少女・夏木とクラスメイトの秦は、ふとしたことから小さな秘密を共有する仲になり……。「新しい日常」の世界を生きる二人の「新しい非日常」の物語が、動き出す!", "nsfw": False, "tags": [
                {"name": "漫画", "count": 22}, {"name": "恋爱", "count": 14}, {"name": "相原瑛人", "count": 9}, {"name": "校园", "count": 6}, {"name": "2020", "count": 4}, {"name": "漫画系列", "count": 4}, {"name": "科幻", "count": 4}, {"name": "一般向", "count": 3}, {"name": "コミックアウル", "count": 3}, {"name": "ファンギルド", "count": 3}, {"name": "JK", "count": 2}],
             "meta_tags": [], "score": 6.7, "score_details": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1, "6": 8, "7": 15, "8": 3, "9": 1, "10": 0}, "rank": 5841, "date": "2021-07-19", "favorite": {"wish": 43, "done": 18, "doing": 55, "on_hold": 11, "dropped": 7}, "series": True},
            {"id": 241596, "type": 2, "name": "Mickey's Trailer", "name_cn": "米奇的房车", "infobox": "{{Infobox animanga/Anime\r\n|中文名= 米奇的房车\r\n|别名={\r\n}\r\n|上映年度= 1938-05-06\r\n|片长= 7分钟\r\n|官方网站= \r\n|其他= \r\n|Copyright= \r\n|类型= 喜剧 / 动画 / 短片 / 家庭 / 冒险\r\n|制片国家/地区= 美国\r\n|语言= 英语\r\n|导演= Ben Sharpsteen\r\n|主演= Pinto Colvig、Walt Disney、Clarence Nash\r\n|IMDb ID= tt0030448\r\n|话数= 1\r\n}}", "platform": 0, "summary": "　　在一个宁静的山间湖泊旁边，耸立着一幢怡人小屋。清晨的阳光洒满大地，从舒适睡眠中醒来的米奇（沃尔特·迪斯尼 Walt Disney 配音）走出房门，伸伸懒腰，随后掣动门前的把手，他的房子便抖动着变成了一辆房车。房车侧面的门打开，一辆黑色的汽车滑了出来，上面坐着米奇的好朋友古菲（品托·考维格 Pinto Colvig 配音）。古菲睁开惺忪的睡眼，按动车上的按钮，令人惊叹的是，后面的青山绿水竟然只是幕布，幕布收入车内，显现出后面被工业所污染破坏的城市。 ",
                "nsfw": False, "tags": [{"name": "欧美", "count": 5}, {"name": "短片", "count": 4}, {"name": "迪士尼", "count": 4}, {"name": "1938", "count": 3}, {"name": "美国", "count": 2}, {"name": "Disney", "count": 2}, {"name": "1930-1939", "count": 1}],
                "meta_tags": [], "score": 7.3, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 2, "7": 3, "8": 3, "9": 1, "10": 0}, "rank": 0, "date": "1938-05-06", "favorite": {"wish": 2, "done": 19, "doing": 0, "on_hold": 0, "dropped": 2}, "series": False},
            {"id": 252220, "type": 4, "name": "月風魔伝", "name_cn": "月风魔传", "infobox": "{{Infobox Game\r\n|中文名= 月风魔传\r\n|别名={\r\n[げつふうまでん]\r\n[Getsu Fūma Den]\r\n[Getsu Fuma Den]\r\n[The Legend of Getsu Fūma]\r\n}\r\n|平台={\r\n[FC]\r\n}\r\n|游戏类型= ARPG\r\n|游戏引擎= \r\n|游玩人数= 1人\r\n|发行日期= 1987年7月7日\r\n|售价= \r\n|website= \r\n|音乐= 前沢秀憲\r\n}}", "platform": 4001, "summary": "《月风魔传》（日语：月風魔伝）是科乐美于1987年在FC推出的动作角色扮演游戏。虽然游戏没有推出续篇，但是在许多后来的科乐美作品中都有参照。", "nsfw": False, "tags": [
                {"name": "FC", "count": 5}, {"name": "ARPG", "count": 5}, {"name": "Konami", "count": 3}, {"name": "游戏", "count": 1}, {"name": "1987", "count": 1}],
                "meta_tags": ["ARPG", "FC", "游戏"], "score": 8.3, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 1, "7": 1, "8": 2, "9": 1, "10": 2}, "rank": 0, "date": "1987-07-07", "favorite": {"wish": 7, "done": 11, "doing": 0, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 252236, "type": 1, "name": "GREASEBERRIES 2", "name_cn": "", "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|出版社= ジーオーティー\r\n|价格= ￥ 3,100\r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2014-10-25\r\n|册数= \r\n|页数= 104\r\n|话数= \r\n|ISBN= 9784860849320\r\n|ISBN-10= 4860849329\r\n|其他= \r\n|作者= 士郎正宗\r\n}}", "platform": 1001,
                "summary": "未発表イラスト、40ページ超の描き下ろしイラストストーリー、貴重なイラストラフ画など、濃艶なフルカラー画集登場!!!!", "nsfw": True, "tags": [{"name": "H", "count": 1}], "meta_tags": [], "score": 6.5, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 1, "6": 0, "7": 0, "8": 1, "9": 0, "10": 0}, "rank": 0, "date": "2014-10-25", "favorite": {"wish": 0, "done": 2, "doing": 0, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 328086, "type": 1, "name": "過剰妄想少年 3", "name_cn": "", "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|作者= ぴい\r\n|出版社= ふゅーじょんぷろだくと; 特装版\r\n|价格= ￥1,200\r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2020-05-24\r\n|册数= \r\n|页数= \r\n|话数= \r\n|ISBN= 9784865896169\r\n|其他= \r\n}}", "platform": 1001, "summary": "シリーズ累計26万部突破!  \" 同棲、始めました。 \"  ドSな執着系男子×妄想癖な元ボッチの大学生編スタート!   [描き下ろし28Pの小冊子付き] 妄想で猫化した大野の性感帯をイタズラしたり、 本編の後日談を収録  ノットハンドオ●ニーしてくれない!?  妄想だけで射精ができる大野(おおの)。その特技を唯一知っている恋人の暮島(くれしま)。 2人は高校を卒業し、別々の大学に通うようになった。 ルームシェアも始めたし、暮島は優しいし、エッチもいっぱいしてくれる。 でも暮島は大学で新しい友人たちに囲まれて忙しそう。 さらに昔は所構わずだった大野への言葉責めもなくなってーー\u003c? br\u003e  少し大人になったけど、お互いのことになると相変わらず空回り。 環境が変わって戸惑う2人の、不器用でまっすぐな恋。", "nsfw": False, "tags": [
                {"name": "BLコミック", "count": 2}, {"name": "BL漫画", "count": 1}, {"name": "ぴい", "count": 1}], "meta_tags": [], "score": 7, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 1, "8": 0, "9": 0, "10": 0}, "rank": 0, "date": "2020-05-24", "favorite": {"wish": 1, "done": 3, "doing": 1, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 328096, "type": 1, "name": "UnderWears HALF", "name_cn": "", "infobox": "{{Infobox animanga/Book\r\n|中文名= \r\n|别名={\r\n}\r\n|出版社= メロンブックス\r\n|价格= 2,750円（税込み）\r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2020-12-26\r\n|页数= 120ページ\r\n|ISBN= \r\n|其他= \r\n|作者= \r\n}}", "platform": 1003, "summary": "全イラスト描きおろし!パンツ特化型画集!\r\n\r\n絶対下着領域\r\n\r\n総勢53作家が贈る、女の子達のかわいいを先生のコメントと共にお届け!\r\n全ての内容が尊すぎるため、ハートの弱い方はご注意を♪",
                "nsfw": False, "tags": [{"name": "画集", "count": 2}], "meta_tags": [], "score": 5, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 2, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0}, "rank": 0, "date": "2020-12-26", "favorite": {"wish": 4, "done": 3, "doing": 0, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 497, "type": 1, "name": "ちょびっツ", "name_cn": "人形电脑天使心", "infobox": "{{Infobox animanga/Manga\r\n|中文名= 人形电脑天使心\r\n|别名={\r\n[en|Chobits]\r\n}\r\n|出版社= 講談社、台灣東販、天下出版\r\n|价格= \r\n|其他出版社= \r\n|连载杂志= 週刊ヤングマガジン\r\n|发售日= 2001-02-06\r\n|册数= 8\r\n|页数= \r\n|话数= 88\r\n|ISBN= \r\n|其他= \r\n|作者= CLAMP\r\n|开始= 2000年第43号\r\n|结束= 2002年第48号\r\n}}", "platform": 1001, "summary": "　　在人型电脑开始量产，人手一台的时代，靠打工养活自己的大学重考生本须和秀树偶然在垃圾场捡到一台女生人型电脑，但是找不到开机钮，在新保的帮忙下得知这台叫「唧」的电脑会令别的电脑当机，而且无法读取资料。于是透过新保介绍自组电脑的高手国分寺稔来帮忙…唧跟着秀树学习，可爱的言行令秀树着迷不已…有一晚，补习老师清水突然要求秀树让她过夜…\r\n\r\n　　可愛さ無敵！の人型パソコン「ちぃ」！――浪人生の本須和秀樹（もとすわ・ひでき）が、近所のゴミ捨て場で拾ってきた、1台の人型パソコン。「ちぃ」と名付け、思いっきり期待したものの、なんのソフトも入っていない役立たずとわかり……！？パソコンが人型をしている世界を舞台にCLAMPが描く、キュートな21世紀型ファンタジック・ラブコメディ！！", "nsfw": False, "tags": [
                {"name": "CLAMP", "count": 182}, {"name": "chobits", "count": 102}, {"name": "漫画", "count": 100}, {"name": "治愈系", "count": 73}, {"name": "科幻", "count": 44}, {"name": "叽", "count": 31}, {"name": "恋爱", "count": 29}, {"name": "最初的感动", "count": 27}, {"name": "爱情", "count": 27}, {"name": "萌的机械耳", "count": 26}, {"name": "治愈", "count": 14}], "meta_tags": [], "score": 7.7, "score_details": {"1": 2, "2": 0, "3": 0, "4": 1, "5": 9, "6": 59, "7": 136, "8": 198, "9": 58, "10": 34}, "rank": 1607, "date": "2001-02-06", "favorite": {"wish": 268, "done": 674, "doing": 47, "on_hold": 33, "dropped": 10}, "series": True}

        ]
        self.test_subject_file = "test_subject_data.jsonlines"
        self.test_subject_index = f"{self.test_subject_file}.index"
        self.test_relation_file = "test_relation_data.jsonlines"
        self.test_relation_index = f"{self.test_relation_file}.index"
        # 创建测试数据文件
        with open(self.test_subject_file, 'wb') as f:
            for item in self.sample_subject_data:
                line = json.dumps(item, ensure_ascii=False).encode(
                    'utf-8') + b'\n'
                f.write(line)

        with open(self.test_relation_file, 'wb') as f:
            for item in self.sample_relation_data:
                line = json.dumps(item, ensure_ascii=False).encode(
                    'utf-8') + b'\n'
                f.write(line)

    def tearDown(self):
        """测试后清理"""
        for f in [self.test_subject_file, self.test_subject_index, self.test_relation_file, self.test_relation_index]:
            if os.path.exists(f):
                os.remove(f)

    @patch('os.path.exists')
    def test_init_without_index_file(self, mock_exists):
        """测试索引查询 - 初始化索引文件(索引不存在)"""
        mock_exists.side_effect = lambda x: x == self.test_subject_file

        reader = IndexedDataReader(self.test_subject_file)
        self.assertTrue(hasattr(reader, 'id_offsets'))
        self.assertIsInstance(reader.id_offsets, dict)

    def test_load_index_file_found(self):
        """测试索引查询 - 加载已有索引文件"""
        import tempfile
        # 构造临时数据文件, 内容为空
        test_data_file = tempfile.NamedTemporaryFile(delete=False)
        test_data_file.write(b'')
        test_data_file.close()

        # 构造测试索引数据
        test_index_data = {
            1: [0, 20],
            2: [40]
        }
        # 构造索引文件路径
        test_index_file = f"{test_data_file.name}.index"

        # 手动写入索引文件
        with open(test_index_file, 'wb') as f:
            pickle.dump(test_index_data, f)

        # 初始化 IndexedDataReader
        reader = IndexedDataReader(test_data_file.name)

        # 验证索引文件正确加载
        self.assertEqual(reader.id_offsets, test_index_data)

    # @patch('tools.log.logger')                       # 模拟日志记录器
    # @patch('pickle.dump')                            # 模拟索引文件写入
    # @patch('builtins.open', new_callable=mock_open)  # 模拟文件操作
    def test_build_offsets_index(self):
        """测试索引查询 - 索引构建功能"""

        # 创建测试实例并触发索引构建
        reader = IndexedDataReader(self.test_subject_file)

        # 验证索引是否成功构建(非空)
        self.assertIsNotNone(reader.id_offsets)

        # 计算预期偏移量
        expected = {}
        current_offset = 0
        for item in self.sample_subject_data:
            item_id = item['id']
            line_bytes = json.dumps(
                item, ensure_ascii=False).encode('utf-8') + b'\n'
            if item_id not in expected:
                expected[item_id] = []
            expected[item_id].append(current_offset)
            current_offset += len(line_bytes)  # 使用字节长度

        # 验证索引构建结果
        self.assertEqual(reader.id_offsets, expected)

    def test_get_data_by_id(self):
        """测试索引查询 - 数据检索功能"""

        # 实际进行测试数据读写
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_id("497", "id")[0]
        self.assertEqual(len(result), 16)
        self.assertEqual(result["name_cn"], "人形电脑天使心")

    def test_invalid_id_conversion(self):
        """测试索引查询 - 无效ID转换"""

        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_id("invalid", "id")
        # 检查返回值
        self.assertEqual(result, [])

    @patch('builtins.open', new_callable=mock_open)
    def test_file_not_found(self, mock_file):
        """测试索引查询 - 数据文件不存在"""
        mock_file.side_effect = FileNotFoundError()
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_id(1, "id")
        self.assertEqual(result, [])


# @unittest.skip("临时跳过测试")
class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        """准备测试数据及文件"""

        self.sample_relation_data = [{"subject_id": 8, "relation_type": 1004, "related_subject_id": 1081, "order": 0},
                                     {"subject_id": 8, "relation_type": 3001,
                                         "related_subject_id": 3219, "order": 6},
                                     {"subject_id": 8, "relation_type": 3004,
                                         "related_subject_id": 8813, "order": 2},
                                     {"subject_id": 8, "relation_type": 3003,
                                      "related_subject_id": 8816, "order": 1},
                                     {"subject_id": 8, "relation_type": 3003,
                                      "related_subject_id": 8817, "order": 2},
                                     {"subject_id": 8, "relation_type": 3099, "related_subject_id": 8819, "order": 15}]
        self.sample_subject_data = [
            {"id": 328150, "type": 1, "name": "ニューノーマル", "name_cn": "新常态", "infobox": "{{Infobox animanga/Manga\r\n|中文名= 新常态\r\n|别名={\r\n[你和我的嘴唇]\r\n[未来的恋爱必须戴口罩]\r\n[New Normal]\r\n}\r\n|出版社= ファンギルド\r\n|价格= \r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2021-07-19\r\n|册数= \r\n|页数= \r\n|话数= \r\n|ISBN= \r\n|其他= \r\n|作者= 相原瑛人\r\n|开始= 2020-12-18\r\n}}", "platform": 1001, "summary": "你的口罩下是住在我心里的那张脸\r\n\r\n「僕たちが生まれる少し前、ひとつの感染症が世界を変えた」――マスクで口元を隠すことが当たり前の日常となった近未来。世界流行\u003cパンデミック\u003e前の時代に密かに思いを馳せる少女・夏木とクラスメイトの秦は、ふとしたことから小さな秘密を共有する仲になり……。「新しい日常」の世界を生きる二人の「新しい非日常」の物語が、動き出す!", "nsfw": False, "tags": [
                {"name": "漫画", "count": 22}, {"name": "恋爱", "count": 14}, {"name": "相原瑛人", "count": 9}, {"name": "校园", "count": 6}, {"name": "2020", "count": 4}, {"name": "漫画系列", "count": 4}, {"name": "科幻", "count": 4}, {"name": "一般向", "count": 3}, {"name": "コミックアウル", "count": 3}, {"name": "ファンギルド", "count": 3}, {"name": "JK", "count": 2}],
             "meta_tags": [], "score": 6.7, "score_details": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1, "6": 8, "7": 15, "8": 3, "9": 1, "10": 0}, "rank": 5841, "date": "2021-07-19", "favorite": {"wish": 43, "done": 18, "doing": 55, "on_hold": 11, "dropped": 7}, "series": True},
            {"id": 241596, "type": 2, "name": "Mickey's Trailer", "name_cn": "米奇的房车", "infobox": "{{Infobox animanga/Anime\r\n|中文名= 米奇的房车\r\n|别名={\r\n}\r\n|上映年度= 1938-05-06\r\n|片长= 7分钟\r\n|官方网站= \r\n|其他= \r\n|Copyright= \r\n|类型= 喜剧 / 动画 / 短片 / 家庭 / 冒险\r\n|制片国家/地区= 美国\r\n|语言= 英语\r\n|导演= Ben Sharpsteen\r\n|主演= Pinto Colvig、Walt Disney、Clarence Nash\r\n|IMDb ID= tt0030448\r\n|话数= 1\r\n}}", "platform": 0, "summary": "　　在一个宁静的山间湖泊旁边，耸立着一幢怡人小屋。清晨的阳光洒满大地，从舒适睡眠中醒来的米奇（沃尔特·迪斯尼 Walt Disney 配音）走出房门，伸伸懒腰，随后掣动门前的把手，他的房子便抖动着变成了一辆房车。房车侧面的门打开，一辆黑色的汽车滑了出来，上面坐着米奇的好朋友古菲（品托·考维格 Pinto Colvig 配音）。古菲睁开惺忪的睡眼，按动车上的按钮，令人惊叹的是，后面的青山绿水竟然只是幕布，幕布收入车内，显现出后面被工业所污染破坏的城市。 ",
                "nsfw": False, "tags": [{"name": "欧美", "count": 5}, {"name": "短片", "count": 4}, {"name": "迪士尼", "count": 4}, {"name": "1938", "count": 3}, {"name": "美国", "count": 2}, {"name": "Disney", "count": 2}, {"name": "1930-1939", "count": 1}],
                "meta_tags": [], "score": 7.3, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 2, "7": 3, "8": 3, "9": 1, "10": 0}, "rank": 0, "date": "1938-05-06", "favorite": {"wish": 2, "done": 19, "doing": 0, "on_hold": 0, "dropped": 2}, "series": False},
            {"id": 252220, "type": 4, "name": "月風魔伝", "name_cn": "月风魔传", "infobox": "{{Infobox Game\r\n|中文名= 月风魔传\r\n|别名={\r\n[げつふうまでん]\r\n[Getsu Fūma Den]\r\n[Getsu Fuma Den]\r\n[The Legend of Getsu Fūma]\r\n}\r\n|平台={\r\n[FC]\r\n}\r\n|游戏类型= ARPG\r\n|游戏引擎= \r\n|游玩人数= 1人\r\n|发行日期= 1987年7月7日\r\n|售价= \r\n|website= \r\n|音乐= 前沢秀憲\r\n}}", "platform": 4001, "summary": "《月风魔传》（日语：月風魔伝）是科乐美于1987年在FC推出的动作角色扮演游戏。虽然游戏没有推出续篇，但是在许多后来的科乐美作品中都有参照。", "nsfw": False, "tags": [
                {"name": "FC", "count": 5}, {"name": "ARPG", "count": 5}, {"name": "Konami", "count": 3}, {"name": "游戏", "count": 1}, {"name": "1987", "count": 1}],
                "meta_tags": ["ARPG", "FC", "游戏"], "score": 8.3, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 1, "7": 1, "8": 2, "9": 1, "10": 2}, "rank": 0, "date": "1987-07-07", "favorite": {"wish": 7, "done": 11, "doing": 0, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 252236, "type": 1, "name": "GREASEBERRIES 2", "name_cn": "", "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|出版社= ジーオーティー\r\n|价格= ￥ 3,100\r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2014-10-25\r\n|册数= \r\n|页数= 104\r\n|话数= \r\n|ISBN= 9784860849320\r\n|ISBN-10= 4860849329\r\n|其他= \r\n|作者= 士郎正宗\r\n}}", "platform": 1001,
                "summary": "未発表イラスト、40ページ超の描き下ろしイラストストーリー、貴重なイラストラフ画など、濃艶なフルカラー画集登場!!!!", "nsfw": True, "tags": [{"name": "H", "count": 1}], "meta_tags": [], "score": 6.5, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 1, "6": 0, "7": 0, "8": 1, "9": 0, "10": 0}, "rank": 0, "date": "2014-10-25", "favorite": {"wish": 0, "done": 2, "doing": 0, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 328086, "type": 1, "name": "過剰妄想少年 3", "name_cn": "", "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|作者= ぴい\r\n|出版社= ふゅーじょんぷろだくと; 特装版\r\n|价格= ￥1,200\r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2020-05-24\r\n|册数= \r\n|页数= \r\n|话数= \r\n|ISBN= 9784865896169\r\n|其他= \r\n}}", "platform": 1001, "summary": "シリーズ累計26万部突破!  \" 同棲、始めました。 \"  ドSな執着系男子×妄想癖な元ボッチの大学生編スタート!   [描き下ろし28Pの小冊子付き] 妄想で猫化した大野の性感帯をイタズラしたり、 本編の後日談を収録  ノットハンドオ●ニーしてくれない!?  妄想だけで射精ができる大野(おおの)。その特技を唯一知っている恋人の暮島(くれしま)。 2人は高校を卒業し、別々の大学に通うようになった。 ルームシェアも始めたし、暮島は優しいし、エッチもいっぱいしてくれる。 でも暮島は大学で新しい友人たちに囲まれて忙しそう。 さらに昔は所構わずだった大野への言葉責めもなくなってーー\u003c? br\u003e  少し大人になったけど、お互いのことになると相変わらず空回り。 環境が変わって戸惑う2人の、不器用でまっすぐな恋。", "nsfw": False, "tags": [
                {"name": "BLコミック", "count": 2}, {"name": "BL漫画", "count": 1}, {"name": "ぴい", "count": 1}], "meta_tags": [], "score": 7, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 1, "8": 0, "9": 0, "10": 0}, "rank": 0, "date": "2020-05-24", "favorite": {"wish": 1, "done": 3, "doing": 1, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 328096, "type": 1, "name": "UnderWears HALF", "name_cn": "", "infobox": "{{Infobox animanga/Book\r\n|中文名= \r\n|别名={\r\n}\r\n|出版社= メロンブックス\r\n|价格= 2,750円（税込み）\r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2020-12-26\r\n|页数= 120ページ\r\n|ISBN= \r\n|其他= \r\n|作者= \r\n}}", "platform": 1003, "summary": "全イラスト描きおろし!パンツ特化型画集!\r\n\r\n絶対下着領域\r\n\r\n総勢53作家が贈る、女の子達のかわいいを先生のコメントと共にお届け!\r\n全ての内容が尊すぎるため、ハートの弱い方はご注意を♪",
                "nsfw": False, "tags": [{"name": "画集", "count": 2}], "meta_tags": [], "score": 5, "score_details": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 2, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0}, "rank": 0, "date": "2020-12-26", "favorite": {"wish": 4, "done": 3, "doing": 0, "on_hold": 0, "dropped": 0}, "series": False},
            {"id": 497, "type": 1, "name": "ちょびっツ", "name_cn": "人形电脑天使心", "infobox": "{{Infobox animanga/Manga\r\n|中文名= 人形电脑天使心\r\n|别名={\r\n[en|Chobits]\r\n}\r\n|出版社= 講談社、台灣東販、天下出版\r\n|价格= \r\n|其他出版社= \r\n|连载杂志= 週刊ヤングマガジン\r\n|发售日= 2001-02-06\r\n|册数= 8\r\n|页数= \r\n|话数= 88\r\n|ISBN= \r\n|其他= \r\n|作者= CLAMP\r\n|开始= 2000年第43号\r\n|结束= 2002年第48号\r\n}}", "platform": 1001, "summary": "　　在人型电脑开始量产，人手一台的时代，靠打工养活自己的大学重考生本须和秀树偶然在垃圾场捡到一台女生人型电脑，但是找不到开机钮，在新保的帮忙下得知这台叫「唧」的电脑会令别的电脑当机，而且无法读取资料。于是透过新保介绍自组电脑的高手国分寺稔来帮忙…唧跟着秀树学习，可爱的言行令秀树着迷不已…有一晚，补习老师清水突然要求秀树让她过夜…\r\n\r\n　　可愛さ無敵！の人型パソコン「ちぃ」！――浪人生の本須和秀樹（もとすわ・ひでき）が、近所のゴミ捨て場で拾ってきた、1台の人型パソコン。「ちぃ」と名付け、思いっきり期待したものの、なんのソフトも入っていない役立たずとわかり……！？パソコンが人型をしている世界を舞台にCLAMPが描く、キュートな21世紀型ファンタジック・ラブコメディ！！", "nsfw": False, "tags": [
                {"name": "CLAMP", "count": 182}, {"name": "chobits", "count": 102}, {"name": "漫画", "count": 100}, {"name": "治愈系", "count": 73}, {"name": "科幻", "count": 44}, {"name": "叽", "count": 31}, {"name": "恋爱", "count": 29}, {"name": "最初的感动", "count": 27}, {"name": "爱情", "count": 27}, {"name": "萌的机械耳", "count": 26}, {"name": "治愈", "count": 14}], "meta_tags": [], "score": 7.7, "score_details": {"1": 2, "2": 0, "3": 0, "4": 1, "5": 9, "6": 59, "7": 136, "8": 198, "9": 58, "10": 34}, "rank": 1607, "date": "2001-02-06", "favorite": {"wish": 268, "done": 674, "doing": 47, "on_hold": 33, "dropped": 10}, "series": True}

        ]
        self.test_subject_file = "test_subject_data.jsonlines"
        self.test_subject_index = f"{self.test_subject_file}.index"
        self.test_relation_file = "test_relation_data.jsonlines"
        self.test_relation_index = f"{self.test_relation_file}.index"
        # 创建测试数据文件
        with open(self.test_subject_file, 'wb') as f:
            for item in self.sample_subject_data:
                line = json.dumps(item, ensure_ascii=False).encode(
                    'utf-8') + b'\n'
                f.write(line)

        with open(self.test_relation_file, 'wb') as f:
            for item in self.sample_relation_data:
                line = json.dumps(item, ensure_ascii=False).encode(
                    'utf-8') + b'\n'
                f.write(line)

    def test_empty_data_file(self):
        """测试索引查询 - 空数据文件"""
        empty_data = "empty.jsonlines"
        reader = IndexedDataReader(empty_data)
        self.assertEqual(reader.id_offsets, {})
        if os.path.exists(f"{empty_data}.index"):
            os.remove(f"{empty_data}.index")

    def test_corrupted_data_file(self):
        """测试索引查询 - 损坏的数据行"""
        import tempfile
        test_corrupt_data = [
            json.dumps(self.sample_subject_data[0]).encode(
                'utf-8') + b'\n',  # 第一行正常解析
            b'invalid json line\n',                           # 第二行损坏
            json.dumps(self.sample_subject_data[2]).encode(
                'utf-8') + b'\n',  # 第三行正常解析
        ]
        # 准备损坏的测试数据
        test_corrupt_data_file = tempfile.NamedTemporaryFile(delete=False)
        test_corrupt_data_file.write(b''.join(test_corrupt_data))
        test_corrupt_data_file.close()

        reader = IndexedDataReader(test_corrupt_data_file.name)

        # 验证索引中包含正确的 ID
        self.assertIn(328150, reader.id_offsets)
        self.assertIn(252220, reader.id_offsets)

        # 调用 get_data_by_id 获取第一行数据
        result = reader.get_data_by_id(328150, "id")
        if not result:
            self.fail("未获取到任何数据, 索引构建可能已失败")

        # 验证结果
        self.assertEqual(len(result[0]), 16)
        self.assertEqual(result[0]["name_cn"], "新常态")

        # 验证只包含两行正确数据的索引
        self.assertEqual(len(reader.id_offsets), 2)
        # 验证损坏行未被索引
        with self.assertRaises(KeyError):
            reader.id_offsets['invalid']

    @patch('os.path.exists')  # 模拟索引文件存在
    @patch('pickle.load')     # 模拟 pickle 加载失败
    def test_corrupted_index_data(self, mock_pickle_load, mock_exists):
        """测试索引查询 - 损坏的索引文件"""
        # 模拟索引文件存在但内容损坏
        mock_exists.return_value = True
        mock_pickle_load.side_effect = pickle.UnpicklingError(
            "Invalid pickle data")

        # 模拟 logger.error
        with patch('tools.log.logger.error') as mock_logger_error:
            # 初始化时应捕获异常并重建索引
            reader = IndexedDataReader(self.test_subject_file)

            # 验证是否调用了重建索引方法
            self.assertTrue(hasattr(reader, 'id_offsets'))
            # 验证索引重建成功
            self.assertIsInstance(reader.id_offsets, dict)
            self.assertIn(328096, reader.id_offsets)

            # 验证是否调用过错误日志
            mock_logger_error.assert_called()

    def test_date_by_index_str(self):
        """测试索引查询 - 字符串ID查询"""
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_id("497", "id")[0]
        self.assertEqual(result["name_cn"], "人形电脑天使心")

    def test_date_by_index_int(self):
        """测试索引查询 - 正常ID查询"""
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_id(497, "id")[0]
        self.assertEqual(result["name_cn"], "人形电脑天使心")

    def tearDown(self):
        """测试后清理"""
        for f in [self.test_subject_file, self.test_subject_index, self.test_relation_file, self.test_relation_index]:
            if os.path.exists(f):
                os.remove(f)
