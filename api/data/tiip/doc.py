from typing import Iterator, Tuple
from colorama import Fore

from params.definitions import ElasticDoc
from errors.data_err import DataError


class DocumentPosSeparator(object):
    """
    Simple class to keep track of positions and length of 
    the separator at that position.
    """

    def __init__(self, position: Tuple[int, int]):
        self.logger = DataError(__file__, self.__class__.__name__)
        if not isinstance(position, tuple):
            self.logger.msg = "Argument 'position' must be of type {}!".format(
                type(tuple).__name__)
            self.logger.error(extra_msg="Got type: {}".format(
                type(position).__name__))
            raise self.logger

        self.pos_obj = position

        self.pos = position[0]
        self.len = position[1]

    def __len__(self):
        return len(self.pos_obj)

    def __lt__(self, other):
        if not isinstance(other, DocumentPosSeparator):
            self.logger.msg = "Cannot compare {} objects to {} objects!".format(
                type(other).__name__, self.__class__.__name__)
            self.logger.error()
            raise self.logger
        return self.pos < other.pos


class DocumentPosSeparatorList(list):
    """
    Class that's meant to keep track of separators and their lengths in
    order to make it easier for other classes to split texts into
    appropriate chunks of text.\n
    :params:\n
    `patterns: tuple(pos: int, pattern_len: int)`
    """

    def __init__(self):
        super().__init__([])
        self.logger = DataError(__file__, self.__class__.__name__)

    def append(self, obj):
        if not isinstance(obj, DocumentPosSeparator):
            self.logger.msg = "Can only add {} objects to a {}!".format(type(DocumentPosSeparator).__name__,
                                                                        self.__class__.__name__)
            self.logger.error(
                extra_msg="Got type: {}".format(type(obj).__name__))
            raise self.logger
        if len(obj) == 2:
            super().append(obj)


class TIIPDocument(object):
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return Fore.LIGHTCYAN_EX + "Content: " + Fore.RESET + self.content

    def __iter__(self):
        yield self


class TIIPDocumentList(list):
    """
    Class that aims to easen the management of singular contents extracted from
    TIIP's different application information documents.
    """

    def __init__(self, init_list: list = []):
        self.logger = DataError(__file__, self.__class__.__name__)
        if len(init_list) > 0:
            self._load_list_arg(init_list)
        else:
            super().__init__([])

    def __iter__(self) -> Iterator[TIIPDocument]:
        for item in super().__iter__():
            yield item

    def _load_list_arg(self, content_list: list):
        for item in content_list:
            if isinstance(item, TIIPDocument):
                self.append(item)
            else:
                converted_item = TIIPDocument(item)
                self.append(converted_item)

    def append(self, obj) -> None:
        if not isinstance(obj, TIIPDocument):
            self.logger.msg = "Items in this list needs to be of type {}!".format(
                TIIPDocument.__name__)
            self.logger.error(
                extra_msg="Got type: {}".format(obj.__class__.__name__))
            raise self.logger
        super().append(obj)

    def to_json(self, index: str) -> list[ElasticDoc]:
        final_list = []
        for doc in self.__iter__():
            final_list.append({
                "vendor_id": index,
                "fields": [{
                    "name": "content",
                    "value": doc.content,
                    "type": "string"
                }]})

        # pprint(final_list)
        # print(type(final_list).__name__)

        if len(final_list) == 0:
            self.logger.msg = "to_json() did NOT generate any results!"
            self.logger.error()
            raise self.logger

        return final_list
