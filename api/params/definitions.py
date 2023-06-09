# This file defines the different parameters that can be sent
# to the app's different endpoints.

from pydantic import BaseModel
from pydantic.typing import Any
from datetime import datetime, timedelta


class ErrorModel(BaseModel):
    error: str


class AddressModel(BaseModel):
    address: str


class BasicResponse(BaseModel):
    msg: str
    data: dict


class Vendor(BaseModel):
    vendor_id: str


class Vendors(BaseModel):
    vendor_ids: list[str]


class Session(BaseModel):
    session: str


class VendorFile(Vendor):
    file: str = ""


class TemplateModel(VendorFile):
    template: str = ""
    sentiment: str = ""
    role: str = ""


class VendorFileQuery(VendorFile):
    query: str = ""


class VendorSession(Vendor, Session):
    pass


class QueryVendorSession(VendorSession):
    query: str
    strict: bool = False


class QueryVendorSessionFile(VendorFileQuery, Session):
    strict: bool = False


class VendorFileSession(VendorSession):
    file: str = ""


class SourceDocument(Vendor):
    filename: str


class AnswersList(BaseModel):
    answers: list[str]
