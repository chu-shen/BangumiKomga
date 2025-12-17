JA_JP = ["日版"]

ZH_HANS = ["bili", "B漫", "汉化", "简中"]

ZH_HANT = [
    "港版",
    "台版",
    "繁中",
    "尖端",
    "东立",
    "東立",
    "东贩",
    "東販",
    "玉皇朝",
    "天下",
    "青文",
    "长鸿",
    "長鴻",
    "角川",
    "文传",
    "文傳",
    "時報",
]


COMIC_KEYWORDS = [
    # 漫画
    "comic",
    "comics",
    "artbook",
    "artbooks",
    "漫画",
    "全彩",
    "全彩版",
    "数码全彩",
    # 部分漫画存在单独的典藏版、爱藏版条目，暂时屏蔽
    # "典藏版",
    # "爱藏版",
]

NOVEL_KEYWORDS = [
    # 小说
    "轻小说",
    "小说",
    "小說",
    "epub",
    "短篇",
    "未完",
    "完结",
    "特典",
    "番外",
]


LANGUAGES_TYPES = [
    ("ja-JP", JA_JP),
    ("zh-Hans", ZH_HANS),
    ("zh-Hant", ZH_HANT),
]

ALL_VOCABULARY = list(set(JA_JP + ZH_HANS + ZH_HANT + COMIC_KEYWORDS + NOVEL_KEYWORDS))
