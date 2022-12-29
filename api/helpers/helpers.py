"""
For helper functions that don't make sense in any other module,
they get put in this module.
"""

import re


def get_language(content: str) -> str:
    """
    Returns a string (`'CH'` or `'EN'`).
    """
    lang = "CH"
    if (len(re.findall(r'[\u4e00-\u9fff]', content)) / len(content)) < 0.5:
        lang = "EN"

    return lang
