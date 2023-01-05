"""
For helper functions that don't make sense in any other module,
they get put in this module.
"""

import re
import sys
from subprocess import check_output
from logging import Logger

from colorama import Fore

logger = Logger(f"{__file__}: ")
logger.warn("Cannot import HelperError!")


def get_language(content: str) -> str:
    """
    Returns a string (`'CH'` or `'EN'`).
    """
    global logger
    logger.name += "get_language()"

    lang = "CH"
    if (len(re.findall(r'[\u4e00-\u9fff]', content)) / len(content)) < 0.5:
        logger.info("Language: English (EN)")
        lang = "EN"
    else:
        logger.info("Language: Traditional Chinese (ZH-TW)")

    return lang


def get_local_ip(org_ip: str) -> str:
    """
    Returns the local IP if the parameter `org_ip`'s value is `0.0.0.0`.
    Otherwise, the original value of `org_ip` is returned.
    """
    global logger
    logger.name += "get_local_ip()"
    platform = sys.platform
    if org_ip == '0.0.0.0' and platform.lower() == "linux":
        local_ip = check_output(
            ["su", "ubuntu", "&&", "ifconfig", "|", "egrep", "'192.168.[0-9]{1,3}.[0-9]{1,3}'", "|", "gawk", "'{print $2}'"])
        logger.info("Platform: " + Fore.LIGHTCYAN_EX + platform + Fore.RESET)
        logger.info("Local IP: " + Fore.LIGHTGREEN_EX + local_ip + Fore.RESET)
        return local_ip
    return org_ip
