"""
Module meant to be used as a shortcut to generate new words through
Claude's OOV service, take the newly generated new terms, words and phrases
and feed them into the ik_smart analyer's dictionairy files (.dic)
"""

from data import CLAUDE_TEST_SERVER, OOV_PORT
from errors.data_err import DataError


class OOVService(object):
    """
    Class meant to handle OOV service tasks.
    """

    def __init__(self, text: str = None):
        self.logger = DataError(__file__, self.__class__.__name__)
        self.server = CLAUDE_TEST_SERVER + ":" + str(OOV_PORT)
        if not isinstance(text, str):
            self.logger.msg = "'text' parameter needs to be of type 'str'!"
            self.logger.error(
                extra_msg="Expected 'str', got '{}'.".format(type(text).__name__))
            raise self.logger
        self.results = self._run(text)

    def _run(self, text: str = None):
        """
        Method designated to send content to Claude & Rupa's OOV service
        to extract eventual new words, terms and/or phrases and add them into
        Elasticsearch's 'ik_smart' analyzer's dictionairy files (.dic).
        """
        # 1. Send request with content to OOV service
        # 2. Send a similar request to Elasticsearch's /_analyze endpoint
        # 3. Compare results by figuring out which terms exist in OOV result
        #       that does not exist in the /_analyze results.
        # 4. Return the words, terms and/or phrases that are new.

    def _send_results(self):
        """
        Method designated to add results from _run() into Elasticsearch's
        'ik_smart' analyzer's dictionairy files (.dic).
        """
        # 1. Open .dic file with content
        # 2. Add content to the file
        # 3. Close file
