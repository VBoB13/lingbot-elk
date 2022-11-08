import uvicorn
from fastapi import FastAPI, Response
from fastapi import status
from params.definitions import Doc, SearchDoc, ErrorModel, BasicResponse
from es.elastic import LingtelliElastic
from . import API_HOST, API_PORT

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/save")
async def save_doc(doc: Doc) -> BasicResponse | ErrorModel:
    try:
        es = LingtelliElastic()
        result = es.save(doc)
    except Exception as err:
        return Response({"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({"msg": "Document saved.", "data": result}, status_code=status.HTTP_201_CREATED)


@app.get("/search")
async def search_doc(doc: SearchDoc) -> BasicResponse | ErrorModel:
    try:
        es = LingtelliElastic()
        result = es.search(index=doc.vendor_id, query=doc.query)
    except Exception as err:
        return Response({"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({"msg": "Document(s) found!", "data": result})

if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT)
