# 词汇表，用于识别漫画的语言类型、内容类型等

## 语言相关
JA_JP = ["日版"]

ZH_HANS_PUBLISHERS = [
    "bili",
    "B漫",
]
ZH_HANS = ["汉化", "简中"]

ZH_HANT_PUBLISHERS = [
    "角川",
    "东立",
    "東立",
    "尖端",
    "玉皇朝",
    "青文",
    "长鸿",
    "長鴻",
    "东贩",
    "東販",
    "天下",
    "文传",
    "文傳",
    "時報",
    "尚禾",
]

ZH_HANT = [
    "港版",
    "台版",
    "繁中",
]

## 内容类型关键词
COMIC_KEYWORDS = [
    "comic",
    "comics",
    "artbook",
    "artbooks",
    "漫画",
    "半彩",
    "全彩",
    "全彩版",
    "数码全彩",
    # 部分漫画存在单独的典藏版、爱藏版、完全版条目
    "电子版",
    "PDF",
    "PDF原档",
]

NOVEL_KEYWORDS = [
    "轻小说",
    "小说",
    "小說",
    "epub",
    "短篇",
    "特典",
    "番外",
]

## 其他
OTHER_KEYWORDS = [
    "未完",
    "完结",
    "完",
]

# 出版社关键词合集
ALL_PUBLISHERS = ZH_HANS_PUBLISHERS + ZH_HANT_PUBLISHERS

# 语言类型映射
LANGUAGE_TYPES = [
    ("ja-JP", JA_JP),
    ("zh-Hans", ZH_HANS_PUBLISHERS + ZH_HANS),
    ("zh-Hant", ZH_HANT_PUBLISHERS + ZH_HANT),
]

# 所有词汇集合（去重）
ALL_VOCABULARY = list(
    set(
        JA_JP
        + ZH_HANS
        + ZH_HANS_PUBLISHERS
        + ZH_HANT
        + ZH_HANT_PUBLISHERS
        + COMIC_KEYWORDS
        + NOVEL_KEYWORDS
        + OTHER_KEYWORDS
    )
)


# 分级关键词
RATING_R18_KEYWORDS = {"R18", "成年コミック", "成人漫画", "本子"}
RATING_R15_KEYWORDS = {"R15", "工口", "エロ", "卖肉", "福利", "后宫"}
