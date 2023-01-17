# This file defines the different parameters that can be sent
# to the app's different endpoints.

from pydantic import BaseModel
from pydantic.typing import Any
from datetime import datetime, timedelta


class ErrorModel(BaseModel):
    error: str


class SearchResultDocTotal(BaseModel):
    value: int
    relation: str


class SearchResultDoc(BaseModel):
    index: str
    id: str
    score: int
    source: dict[str, Any]


class SearchResponseDoc(BaseModel):
    total: SearchResultDocTotal
    max_score: int
    hits: list[SearchResultDoc]


class BasicResponse(BaseModel):
    msg: str
    data: dict


class SearchResponse(BaseModel):
    msg: str
    data: SearchResponseDoc


class Vendor(BaseModel):
    vendor_id: str


class Vendors(BaseModel):
    vendor_ids: list[str]


class DocID(BaseModel):
    doc_id: str | None = None


class DocID_Must(Vendor):
    doc_id: str


class Field(BaseModel):
    name: str
    value: str | int
    type: str | None = None


class ElasticDoc(Vendor):
    fields: list[Field]
    source: str = ""


class SearchField(BaseModel):
    name: str
    search_term: str
    operator: str = "OR"
    min_should_match: int = 1


class SearchDocument(Vendor):
    match: SearchField


class SearchGPT(SearchDocument):
    strict: bool = False


class SearchPhraseDoc(Vendor):
    match_phrase: str


class SearchPhraseFieldDoc(SearchPhraseDoc):
    field: str


class SearchDocTimeRange(Vendor):
    start: str = (datetime.now() - timedelta(days=1)
                  ).strftime("%Y-%m-%dT%H:%M:%S")
    end: str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
