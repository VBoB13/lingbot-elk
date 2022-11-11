# This file defines the different parameters that can be sent
# to the app's different endpoints.

from pydantic import BaseModel
from pydantic.typing import Any, Optional
from datetime import datetime, timedelta


class ErrorModel(BaseModel):
    error: str


class SearchResultDoc(BaseModel):
    _index: str
    _id: str
    _score: int
    _source: dict[str, Any]


class SearchResponseDoc(BaseModel):
    total: dict[str, Any]
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
    doc_id: Optional[str] = None


class Field(BaseModel):
    name: str
    value: str | int
    type: Optional[str] = None


class ElasticDoc(Vendor, DocID):
    fields: list[Field]


class SearchDocTimeRange(Vendor):
    start: str = (datetime.now() - timedelta(hours=1)
                  ).strftime("%Y-%m-%dT%H:%M:%S")
    end: str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
