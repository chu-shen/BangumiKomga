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
        return None
    
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
        return None
    
    # ADAPTATION      = (1,  "改编") # FIXME 源数据没有区分动画、书籍、游戏
    SERIES          = (1002, "系列")
    OFFPRINT        = (1003, "单行本")
    ALBUM           = (1004, "画集")
