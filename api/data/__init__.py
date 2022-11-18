import re

Q_SEP = ".Q："
A_SEP = "A："

DOC_SEP = "\n"
DOC_SEP_LIST_1 = ["壹、", "貳、", "參、", "肆、", "伍、",
                  "陸、", "柒、", "捌、", "玖、", "拾、"]

DOC_SEP_LIST_2 = [re.compile(
    ".*[一二三四五六七八九十]{1,3}、.*"), re.compile(".*附件[一二三四五六七八九十]+[:：].*")]

DOC_SEP_LIST_3 = [re.compile(".*\([一二三四五六七八九十]{1,2}\).*")]
