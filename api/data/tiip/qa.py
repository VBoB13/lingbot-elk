# File meant to make life easier to handle the specific Question+Answer
# objects retrieved through parsing PDF files.
from typing import List

from errors.data_err import DataError


class TIIP_QA_Pair(object):
    def __init__(self, pair_text: str):
        super().__init__()
        self.logger = DataError(__file__, self.__class__.__name__)
        if not (isinstance(pair_text, str) and len(pair_text) > 0):
            self.logger.msg = "Each QA pair object needs to be of type 'str' and cannot be empty!"
            self.logger.error()
            raise self.logger
        self.source = pair_text
        self._process_qa_pair()
        self.question = None
        self.answer = None

    def __str__(self):
        return "Q: {}\nA:{}".format(self.question, self.answer)

    def _process_qa_pair(self):
        """
        Method actually in charge of making the QA pair by locating the
        'Q' and 'A' part of the text and then setting them as attributes
        `.question` and `.answer`.
        """
        pass


class TIIP_QA_PairList(list):
    def __init__(self, qa_pair_list: List):
        super().__init__([])
        self.logger = DataError(__file__, self.__class__.__name__)
        for pair in qa_pair_list:
            print(pair)
