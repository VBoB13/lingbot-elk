import re
from re import Pattern

Q_SEP = ".Q："
A_SEP = "A："

DOC_SEP = "\n"

# DOC_SEP_LIST_1 = [re.compile(
#     r"[壹貳參肆伍陸柒捌玖拾]{1,2}、", flags=re.MULTILINE)]

INIT_SEP_LIST_STR = ['壹、', '貳、', '參、', '肆、',
                     '伍、', '陸、', '柒、', '捌、', '玖、', '拾、']

DOC_SEP_LIST: list[Pattern] = [
    [re.compile(r"[壹貳參肆伍陸柒捌玖拾]{1}、", re.MULTILINE)],
    [re.compile(r"[一二三四五六七八九十]{1,3}、", re.MULTILINE)],
    [re.compile(r"\([一二三四五六七八九十]{1,2}\)", re.MULTILINE)],
    [re.compile(r"[0-9]+\. ", re.MULTILINE)]
]

ADD_DOCS_SEP_LIST: list[list[Pattern]] = [
    [re.compile(r"附件[一二三四五六七八九十]{1,2}[:：]", re.MULTILINE)],
    [re.compile(r"第[一二三四五六七八九十]{1}章", re.MULTILINE)],
    [
        re.compile(r"第[一二三四五六七八九十]{1,3}條", re.MULTILINE),
        re.compile(r"[一二三四五六七八九十]{1,2}、", re.MULTILINE)
    ]
]

DOC_LENGTH = int(7)
