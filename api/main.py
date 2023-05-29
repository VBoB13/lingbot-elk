import os
import uvicorn
import shutil
import logging

from fastapi import FastAPI, status, BackgroundTasks, UploadFile, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from params import DESCRIPTIONS
from params.definitions import BasicResponse, SearchGPT2, SourceDocument, QueryVendorSession, VendorFileSession, VendorFileQuery, TemplateModel, QueryVendorSessionFile
from es.elastic import LingtelliElastic
from es.lc_service import FileLoader, LingtelliElastic2
from settings.settings import TEMP_DIR
from helpers.reqres import ElkServiceResponse
from data.importer import CSVLoader, WordDocumentReader, TIIPDocumentList
from errors.errors import BaseError


app = FastAPI()
test_client = TestClient(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logging.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


logger = BaseError(__file__, "main")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/delete_bot", response_model=BasicResponse, description=DESCRIPTIONS["/delete_bot"])
async def delete_bot(delete_obj: VendorFileSession):
    global logger
    logger.cls = "main.py:delete_bot"
    try:
        es = LingtelliElastic2()
        es.delete_bot(delete_obj.vendor_id,
                      delete_obj.file, delete_obj.session)
        return ElkServiceResponse(content={"msg": "Deleted bot data successfully!", "data": {"vendor_id": delete_obj.vendor_id, "file": delete_obj.file, "session": delete_obj.session}}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.msg = "Could NOT delete data from bot ID: <%s>!" % delete_obj.vendor_id
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/delete_source", response_model=BasicResponse, description=DESCRIPTIONS["/delete_source"])
async def delete_source(source: SourceDocument):
    global logger
    logger.cls = "main.py:delete_source"
    try:
        es = LingtelliElastic2()
        es.delete_bot(source.vendor_id,
                      source.filename)
        return ElkServiceResponse(
            content={
                "msg": "Deleted bot INFO data successfully!",
                "data": {"vendor_id": source.vendor_id, "file": source.filename}},
            status_code=status.HTTP_200_OK
        )
    except Exception as err:
        logger.msg = "Could NOT delete INFO data from bot ID: <%s>!" % source.vendor_id
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search-file", response_model=BasicResponse, description=DESCRIPTIONS["/search-file"])
async def search_doc_file(doc: VendorFileQuery):
    global logger
    logger.cls = "main.py:search_doc_gpt"
    try:
        es = LingtelliElastic2()
        answer, finish_time = es.embed_search_with_sources(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": answer, "Time": str(finish_time)+"s"}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"msg": "Unexpected ERROR occurred!", "data": {"error": str(err)}}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search-gpt", response_model=BasicResponse, description=DESCRIPTIONS["/search-gpt"])
async def search_doc_gpt(doc: QueryVendorSessionFile):
    global logger
    logger.cls = "main.py:search_doc_gpt"
    try:
        es = LingtelliElastic2()
        answer = es.search_gpt(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": answer}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"msg": "Unexpected ERROR occurred!", "error": str(err)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/set-template", response_model=BasicResponse, description=DESCRIPTIONS["/set-template"])
async def set_template(template_obj: TemplateModel):
    global logger
    logger.cls = "main.py:set_template"

    try:
        es = LingtelliElastic2()
        final_index = es.set_template(template_obj)
    except Exception as err:
        logger.msg = "Something went wrong when trying to set template!"
        logger.error(extra_msg=str(err), orgErr=err)
        ElkServiceResponse(content={"msg": "Unexpected ERROR occurred!", "error": "{}: {}".format(
            logger.msg, err.msg if isinstance(err, BaseError) else str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return ElkServiceResponse(content={"msg": "Template successfully set! (index: {})!".format(final_index)}, status_code=status.HTTP_202_ACCEPTED)


@app.post("/upload", description=DESCRIPTIONS["/upload"])
async def upload(index: str, file: UploadFile, bg_tasks: BackgroundTasks):
    global logger
    logger.cls = "main.py:upload"

    # Make sure index (vendor_id) is lowercase (Elasticsearch)
    if index != index.lower():
        logger.msg = "Index needs to be lowercase!"
        logger.error()
        return ElkServiceResponse(content={"msg": "Unexpected ERROR occurred!", "error": "{}".format(logger.msg)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        FileLoader(file, index)
    except Exception as err:
        logger.msg = "Something went wrong when trying to save file contents into ELK!"
        logger.error(extra_msg=str(err), orgErr=err)
        ElkServiceResponse(content={"msg": "Unexpected ERROR occurred!", "error": "{}: {}".format(
            logger.msg, err.msg if isinstance(err, BaseError) else str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return ElkServiceResponse(content={"msg": "Documents successfully uploaded & saved into ELK (index: {})!".format(index)}, status_code=status.HTTP_202_ACCEPTED)


if __name__ == "__main__":
    API_HOST = os.environ.get("API_SERVER", "0.0.0.0")
    API_PORT = int(os.environ.get("API_PORT", "420"))
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, workers=2)
