# File meant to make life easier to handle the specific Question+Answer
# objects retrieved through parsing PDF files.
from pprint import pprint
from typing import List, Iterator
from colorama import Fore

from params.definitions import ElasticDoc
from errors.errors import DataError


class TIIP_QA_Pair(object):
    def __init__(self, question: str, answer: str):
        super().__init__()
        self.logger = DataError(__file__, self.__class__.__name__)
        self.question = question
        self.answer = answer

    def __str__(self):
        return Fore.LIGHTCYAN_EX + "Q: " + Fore.RESET + f"{self.question}\n" \
            + Fore.LIGHTRED_EX + "A:" + Fore.RESET + \
            f" {self.answer}"

    def __iter__(self):
        yield self.question, self.answer


class TIIP_QA_PairList(list):
    def __init__(self, qa_pair_list: List = None):
        """
        Constructor for TIIP_QA_PairList.
        If you pass a `list` as an argument, make sure the structure follow
        the following pattern:
        `[{"q": "...", "a", "..."}, ...]`
        """
        super().__init__([])
        self.logger = DataError(__file__, self.__class__.__name__)
        if qa_pair_list is not None and isinstance(qa_pair_list, list):
            self._load_list_arg(qa_pair_list)

    def __iter__(self) -> Iterator[TIIP_QA_Pair]:
        for item in super().__iter__():
            yield item

    def _load_list_arg(self, qa_pair_list: list):
        for item in qa_pair_list:
            if isinstance(item, TIIP_QA_Pair):
                self.append(item)
            else:
                converted_item = TIIP_QA_Pair(item["q"], item["a"])
                self.append(converted_item)

    def append(self, obj) -> None:
        if not isinstance(obj, TIIP_QA_Pair):
            self.logger.msg = "Items in this list needs to be of type {}!".format(
                TIIP_QA_Pair.__name__)
            self.logger.error(
                extra_msg="Got type: {}".format(obj.__class__.__name__))
            raise self.logger
        super().append(obj)

    def to_json(self, index: str = None) -> list[ElasticDoc]:
        final_list = []
        for qa_pair in self.__iter__():
            if index is None:
                final_list.append({"q": qa_pair.question, "a": qa_pair.answer})
                continue

            final_list.append({
                "vendor_id": index,
                "fields": [{
                    "name": "q",
                    "value": qa_pair.question,
                    "type": "string"
                }, {
                    "name": "a",
                    "value": qa_pair.answer,
                    "type": "string"
                }]})

        # pprint(final_list)
        # print(type(final_list).__name__)

        if len(final_list) == 0:
            self.logger.msg = "to_json() did NOT generate any results!"
            self.logger.error()
            raise self.logger

        return final_list
