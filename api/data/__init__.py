import re
import re
import os

CLAUDE_TEST_SERVER = os.environ.get('CLAUDE_TEST_SERVER', None)
OOV_PORT = 3333

Q_SEP = ".Q："
A_SEP = "A："

DOC_SEP = "\n"

# DOC_SEP_LIST_1 = [re.compile(
#     r"[壹貳參肆伍陸柒捌玖拾]{1,2}、", flags=re.MULTILINE)]

DOC_SEP_LIST_1 = ['壹、', '貳、', '參、', '肆、',
                  '伍、', '陸、', '柒、', '捌、', '玖、', '拾、']

DOC_SEP_LIST_2 = [re.compile(
    r"[一二三四五六七八九十]{1,3}、", re.MULTILINE), re.compile(r"附件[一二三四五六七八九十]+[:：]", re.MULTILINE)]

DOC_SEP_LIST_3 = [re.compile(r"\([一二三四五六七八九十]{1,2}\)", re.MULTILINE)]

DOC_SEP_LIST_4 = [re.compile(r"[0-9]+\. ", re.MULTILINE)]

DOC_LENGTH = int(7)

TIIP_FTP_SERVER = os.environ.get('FTP_SERVER')
TIIP_FTP_ACC = os.environ.get('TIIP_FTP_ACC')
TIIP_FTP_PASS = os.environ.get('TIIP_FTP_PASS')
