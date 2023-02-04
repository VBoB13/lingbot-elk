"""
This module is made to make certain interactive choices when running singular scripts easier
within the project (especially file loaders).
"""

from helpers import INTERACTIVE_ANSWERS, YES_ANSWERS
from errors.errors import HelperError


def question_check(question: str) -> bool:
    """
    Function that simply asks a question and expects
    a [Y] or an [N] for answer.\n
    Parameters:\n
    `question <str>` : Question to be asked in command prompt.
    """
    logger = HelperError(__file__, "helpers.interactive:question_check")
    answer = input(question + "\n(Y/N): ")
    while answer not in INTERACTIVE_ANSWERS:
        logger.msg = "Only the following answers are accepted: {}".format(
            str(INTERACTIVE_ANSWERS))
        logger.warning()
        answer = input(question + "\n(Y/N): ")

    if answer in YES_ANSWERS:
        return True
    return False
