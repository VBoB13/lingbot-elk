import os
import uvicorn
import shutil

from fastapi import FastAPI, status, BackgroundTasks, UploadFile
from fastapi.testclient import TestClient
from colorama import Fore

from params import DESCRIPTIONS
from params.definitions import ElasticDoc, SearchDocTimeRange, SearchDocument, \
    DocID_Must, BasicResponse, SearchResponse, \
    SearchPhraseDoc, SearchGPT, Vendor, SourceDocument
from es.elastic import LingtelliElastic
from settings.settings import TEMP_DIR, TIIP_CSV_DIR
from helpers.reqres import ElkServiceResponse
from data.importer import CSVLoader, WordDocumentReader, TIIPDocumentList
from errors.errors import BaseError


app = FastAPI()
test_client = TestClient(app)
logger = BaseError(__file__, "main")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/delete", response_model=BasicResponse, description=DESCRIPTIONS["/delete"])
async def delete_index(vendor: Vendor):
    global logger
    logger.cls = "main.py:delete_index"
    try:
        es = LingtelliElastic()
        es.delete_index(vendor.vendor_id)
        return ElkServiceResponse(content={"msg": "Index deleted.", "data": vendor.vendor_id}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.msg = "Could NOT delete index <%s>!" % vendor.vendor_id
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/delete_source", response_model=BasicResponse, description=DESCRIPTIONS["/delete_source"])
async def delete_source(source: SourceDocument):
    global logger
    logger.cls = "main.py:delete_source"
    try:
        es = LingtelliElastic()
        es.delete_source(source.vendor_id, source.filename)
        return ElkServiceResponse(content={"msg": "Documents from source file [%s] deleted!" % (Fore.LIGHTGREEN_EX + source.filename + Fore.RESET), "data": source.vendor_id}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.msg = "Could NOT delete index <%s>!" % source.vendor_id
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/save", response_model=BasicResponse, description=DESCRIPTIONS["/save"])
async def save_doc(doc: ElasticDoc):
    global logger
    logger.cls = "main.py:save_doc"
    try:
        es = LingtelliElastic()
        result = es.save(doc)
        return ElkServiceResponse(content={"msg": "Document saved.", "data": result}, status_code=status.HTTP_201_CREATED)
    except Exception as err:
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/save-bulk", response_model=BasicResponse, description=DESCRIPTIONS["/save-bulk"])
async def save_bulk(docs: list[ElasticDoc]):
    global logger
    logger.cls = "main.py:save_bulk"
    try:
        es = LingtelliElastic()
        result = es.save_bulk(docs)
        return ElkServiceResponse(content={"msg": "Document saved.", "data": result}, status_code=status.HTTP_201_CREATED)
    except Exception as err:
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/get", description=DESCRIPTIONS["/get"])
async def get_doc(doc: DocID_Must):
    global logger
    logger.cls = "main.py:get_doc"
    try:
        es = LingtelliElastic()
        result = es.get(doc)
        return ElkServiceResponse(content={"msg": "Document found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        if hasattr(err, 'msg') and err.msg == "Could not get any documents!":
            return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_204_NO_CONTENT)
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search", response_model=BasicResponse, description=DESCRIPTIONS["/search"])
async def search_doc(doc: SearchDocument):
    global logger
    logger.cls = "main.py:search_doc"
    try:
        es = LingtelliElastic()
        result = es.search(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        if hasattr(err, 'msg') and not es.docs_found:
            return ElkServiceResponse(content={"error": "{}".format(err.msg)}, status_code=status.HTTP_204_NO_CONTENT)
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search-gpt", response_model=BasicResponse, description=DESCRIPTIONS["/search-gpt"])
async def search_doc_gpt(doc: SearchGPT):
    global logger
    logger.cls = "main.py:search_doc_gpt"
    try:
        es = LingtelliElastic()
        result = es.search_gpt(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        if hasattr(err, 'msg') and not es.docs_found:
            return ElkServiceResponse(content={"msg": f"{err.msg}", "data": {"error": str(err)}}, status_code=status.HTTP_204_NO_CONTENT)
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"msg": "Unexpected ERROR occurred!", "data": {"error": str(err)}}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search/phrase", description=DESCRIPTIONS["/search/phrase"])
async def search_phrase(doc: SearchPhraseDoc):
    global logger
    logger.cls = "main.py:search_phrase"
    try:
        es = LingtelliElastic()
        result = es.search_phrase(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        if hasattr(err, 'msg') and err.msg == "Could not get any documents!":
            return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_204_NO_CONTENT)
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search/timespan", response_model=SearchResponse, description=DESCRIPTIONS["/search/timespan"])
async def search_doc_timerange(doc: SearchDocTimeRange):
    global logger
    logger.cls = "main.py:search_doc_timerange"
    try:
        es = LingtelliElastic()
        result = es.search_timerange(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/upload/csv", description=DESCRIPTIONS["/upload/csv"])
def upload_csv(index: str, file: UploadFile, bg_tasks: BackgroundTasks):
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
