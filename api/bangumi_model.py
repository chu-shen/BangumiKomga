from enum import Enum


class SubjectPlatform(Enum):
    """
    条目平台 枚举类
    https://github.com/bangumi/common/blob/master/subject_platforms.yml
    """

    def __new__(cls, value, cn):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cn = cn
        return obj

    @classmethod
    def parse(cls, value):
        """
        根据值或中文名解析枚举
        """
        for member in cls:
            if value == member.value or value == member.cn:
                return member
        return UnprocessedType.BGM38

    Tv              = (1 ,"TV")
    OVA             = (2 ,"OVA")
    Movie           = (3 ,"剧场版")
    Web             = (5 ,"Web")
    Comic           = (1001 ,"漫画")
    Novel           = (1002 ,"小说")
    Illustration    = (1003 ,"画集")
    Game            = (4001 ,"游戏")

class SubjectRelation(Enum):
    """
    条目之间的关联 枚举类
    https://github.com/bangumi/common/blob/master/subject_relations.yml
    """

    def __new__(cls, value, cn):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cn = cn
        return obj

    @classmethod
    def parse(cls, value):
        """
        根据值或中文名解析枚举
        """
        for member in cls:
            if value == member.value or value == member.cn:
                return member
        return UnprocessedType.BGM38

    # bangumi/Archive 中改编没有区分动画、书籍、游戏，需要元数据中的 type(BangumiBaseType) 字段辅助判断
    ADAPTATION      = (1,  "改编")
    SERIES          = (1002, "系列")
    OFFPRINT        = (1003, "单行本")
    ALBUM           = (1004, "画集")

    OnlineAPIBook   = (1, "书籍")
    OnlineAPIAnime  = (1, "动画")


class BangumiBaseType(Enum):
    """
    bangumi 条目类型 枚举类
    """
    def __new__(cls, value, cn):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cn = cn
        return obj

    @classmethod
    def parse(cls, value):
        """
        根据值或中文名解析枚举
        """
        for member in cls:
            if value == member.value or value == member.cn:
                return member
        return UnprocessedType.BGM38

    BOOK             = (1 ,"书籍")
    ANIME            = (2 ,"动画")
    MUSIC            = (3 ,"音乐")
    GAME             = (4 ,"游戏")
    REAL             = (6 ,"三次元")


class UnprocessedType(Enum):
    """
    未处理类型 枚举类
    """
    def __new__(cls, value, cn):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cn = cn
        return obj

    BGM38           = (2333 ,"bgm38")
