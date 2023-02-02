from starlette.datastructures import UploadFile
from typing import Iterator, Tuple
from colorama import Fore

from api.params.definitions import ElasticDoc
from api.errors.errors import DataError


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

    def __str__(self):
        return "{}".format(self.pos)

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

    def __str__(self) -> str:
        return self.content

    def __iter__(self):
        yield "content", self.content


class TIIPDocumentList(list):
    """
    Class that aims to easen the management of singular contents extracted from
    TIIP's different application information documents.
    """

    def __init__(self, init_list: list = [], source: str = ""):
        self.logger = DataError(__file__, self.__class__.__name__)
        self.source = source.filename if isinstance(
            source, UploadFile) else str(source)
        if len(init_list) > 0:
            self._load_list_arg(init_list)
        else:
            self.logger.msg = "Initializing empty list."
            self.logger.warn()
            super().__init__([])

    def __iter__(self) -> Iterator[TIIPDocument]:
        for item in super().__iter__():
            yield item

    def __str__(self) -> str:
        string = ""
        for doc in self.__iter__():
            string += Fore.LIGHTCYAN_EX + "Content:\n" + \
                Fore.RESET + "{}\n\n".format(str(doc))
        return string

    def _load_list_arg(self, content_list: list):
        for item in content_list:
            if isinstance(item, TIIPDocument):
                self.append(item)
            else:
                self.append(TIIPDocument(item))

    def append(self, obj) -> None:
        if not isinstance(obj, TIIPDocument):
            self.logger.msg = "Items in this list needs to be of type {}!".format(
                TIIPDocument.__name__)
            self.logger.error(
                extra_msg="Got type: {}".format(obj.__class__.__name__))
            raise self.logger
        super().append(obj)

    def to_json(self, index: str, source: str = "") -> list[ElasticDoc]:
        """
Takes the content of the list and returns a doctionary formatted as:\n
`{"vendor_id": index,\n
\t"fields":[{\n
\t\t"name": <string>,\n
\t\t"value": <TIIPDocument.content: str>,\n
\t\t"type": <string: 'string'|'integer'>\n
\t}]
}`
        """
        if len(self) == 0:
            self.logger.msg = "to_json() did NOT generate any results!"
            self.logger.error()
            raise self.logger

        source = str(source.filename) if isinstance(
            source, UploadFile) else source
        self.source = str(self.source.filename) if isinstance(
            self.source, UploadFile) else self.source

        if len(source) == 0 and len(self.source) > 0:
            source = self.source

        final_list = []
        for doc in self.__iter__():
            final_list.append({
                "vendor_id": index,
                "fields": [{
                    "name": "content",
                    "value": doc.content,
                    "type": "text",
                    "main": True,
                    "searchable": True
                }, {
                    "name": "source",
                    "value": source,
                    "type": "keyword",
                    "main": False,
                    "searchable": True
                }]})

        # pprint(final_list)
        # print(type(final_list).__name__)

        return final_list
