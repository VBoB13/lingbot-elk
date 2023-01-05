"""
For helper functions that don't make sense in any other module,
they get put in this module.
"""

import re
import sys
from subprocess import check_output

from colorama import Fore

from errors.errors import HelperError

logger = HelperError(__file__, "")


def get_language(content: str) -> str:
    """
    Returns a string (`'CH'` or `'EN'`).
    """
    global logger
    logger.cls = "get_language()"
    logger.msg = "Resolved language to: "
    lang = "CH"
    if (len(re.findall(r'[\u4e00-\u9fff]', content)) / len(content)) < 0.5:
        logger.msg += "English (EN)"
        lang = "EN"
    else:
        logger.msg += "Traditional Chinese (ZH-TW)"

    logger.info()

    return lang


def get_local_ip(org_ip: str) -> str:
    """
    Returns the local IP if the parameter `org_ip`'s value is `0.0.0.0`.
    Otherwise, the original value of `org_ip` is returned.
    """
    global logger
    logger.cls += "get_local_ip()"
    platform = sys.platform
    if org_ip == '0.0.0.0' and platform.lower() == "linux":
        local_ip = check_output(
            ["ifconfig", "|", "egrep", "192.168.[0-9]{1,3}.[0-9]{1,3}", "|", "gawk", "'{print $2}'"])
        logger.msg = "Platform: " + Fore.LIGHTCYAN_EX + platform + Fore.RESET
        logger.info()
        logger.msg = "Local IP: " + Fore.LIGHTGREEN_EX + local_ip + Fore.RESET
        logger.info()
        return local_ip
    return org_ip
