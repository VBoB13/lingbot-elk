# This file defines the different parameters that can be sent
# to the app's different endpoints.

from pydantic import BaseModel
from pydantic.typing import Any, Optional


class ErrorModel(BaseModel):
    error: str


class BasicResponse(BaseModel):
    msg: str
    data: dict[str, Any]


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


class SearchDoc(Vendor):
    query: str = {"match_all": {}}
