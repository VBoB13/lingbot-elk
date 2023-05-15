import os
import uvicorn
import shutil
import logging

from fastapi import FastAPI, status, BackgroundTasks, UploadFile, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from params import DESCRIPTIONS
from params.definitions import BasicResponse, SearchGPT2, SourceDocument, QueryVendorSession, VendorFileSession, VendorFileQuery
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
async def search_doc_gpt(doc: QueryVendorSession):
    global logger
    logger.cls = "main.py:search_doc_gpt"
    try:
        es = LingtelliElastic2()
        answer = es.search_gpt(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": answer}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"msg": "Unexpected ERROR occurred!", "data": {"error": str(err)}}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/upload", description=DESCRIPTIONS["/upload"])
async def upload(index: str, file: UploadFile):
    global logger
    logger.cls = "main.py:upload"

    # Make sure index (vendor_id) is lowercase (Elasticsearch)
    if index != index.lower():
        logger.msg = "Index needs to be lowercase!"
        logger.error()
        return ElkServiceResponse(content={"error": "{}".format(logger.msg)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        FileLoader(file, index)
    except Exception as err:
        logger.msg = "Something went wrong when trying to save file contents into ELK!"
        logger.error(extra_msg=str(err), orgErr=err)
        ElkServiceResponse(content={"error": "{}: {}".format(logger.msg, err.__getattribute__('msg', 'N/A'))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return ElkServiceResponse(content={"msg": "Documents successfully uploaded & saved into ELK (index: {})!".format(index)}, status_code=status.HTTP_202_ACCEPTED)


@app.post("/upload/csv", description=DESCRIPTIONS["/upload/csv"])
async def upload_csv(index: str, file: UploadFile, bg_tasks: BackgroundTasks):
    global logger
    logger.cls = "main.py:upload_csv"
    try:
        # Recieve and parse the csv file
        # Check for correct file type
        if file and file.filename.endswith(".csv"):
            temp_name = os.path.join(TEMP_DIR, index, file.filename)
            if not os.path.isdir(os.path.join(TEMP_DIR, index)):
                os.mkdir(os.path.join(TEMP_DIR, index))

            try:
                # Copy contents into a temporary file
                with open(temp_name, 'xb') as f:
                    shutil.copyfileobj(file.file, f)

            except Exception as err:
                logger.msg = "Something went wrong when trying to copy contents of file!"
                logger.error(orgErr=err)
                raise logger from err
            else:
                # Load the contents of the temp. file
                csv_obj = CSVLoader(index, temp_name)
                bg_tasks.add_task(csv_obj.save_bulk)
            finally:
                # Close file for read/write
                file.file.close()
                # Remove the temp. file afterwards
                os.remove(temp_name)
                os.rmdir(os.path.join(TEMP_DIR, index))

        else:
            logger.msg = "File must be of type '.csv'; not '.{}'!".format(
                file.filename.split(".")[1])
            logger.error()
            raise logger

    except Exception as err:
        logger.msg = "Could not save CSV content into Elasticsearch!"
        logger.error(orgErr=err)
        logger.save_log(index, str(logger))
        raise logger from err

    return ElkServiceResponse(content={"msg": "Documents successfully uploaded & saved into ELK (index: {})!".format(index)}, status_code=status.HTTP_202_ACCEPTED)


@app.post("/upload/docx", description=DESCRIPTIONS["/upload/docx"])
async def upload_docx(index: str, file: UploadFile):
    global logger
    logger.cls = "main.py:upload_docx"
    if file.filename.endswith(".docx"):
        try:
            # Receive and parse the .docx file
            content_list = WordDocumentReader().extract_text(index, file)
            # Convert into document list
            doc_list = TIIPDocumentList(content_list, source=file.filename)
            # Convert into ELK format
            elk_doc_list = doc_list.to_json(index)
            # Create client instance and save documents
            client = LingtelliElastic()
            client.save_bulk(elk_doc_list)
        except Exception as err:
            logger.msg = "Unable to save {}'s content into ELK!".format(
                file.filename)
            logger.error(orgErr=err)
            logger.save_log(index, str(logger))
            raise logger from err
        else:
            logger.msg = "Content from {} saved into ELK!".format(
                file.filename)
            logger.info(
                extra_msg="{} documents were saved!".format(len(doc_list)))

        return ElkServiceResponse(content={"msg": "Document successfully uploaded & saved into ELK (index: {})!".format(index)}, status_code=status.HTTP_200_OK)


if __name__ == "__main__":
    API_HOST = os.environ.get("API_SERVER", "0.0.0.0")
    API_PORT = int(os.environ.get("API_PORT", "420"))
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, workers=2)
