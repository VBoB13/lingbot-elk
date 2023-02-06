import os
import json

from fastapi.testclient import TestClient

from api.es.elastic import LingtelliElastic
from api.settings.settings import TIIP_CSV_DIR
from api.main import app

test_client = TestClient(app)


def test_upload_csv():
    index = "test-upload-csv-index"
    # Create file object to throw to endpoint
    files = {'file': open(os.path.join(TIIP_CSV_DIR, '通用.csv'), 'rb')}
    response = test_client.post('/upload/csv?index=%s' % index, files=files)
    check_result = {
        "msg": "Documents successfully uploaded & saved into ELK (index: %s)!" % index}

    assert check_result == response.json()

    # Initiate ELK client
    elk_client = LingtelliElastic()
    if elk_client.index_exists(index):
        data = json.dumps({'vendor_id': index})
        # Delete index if it exists
        response = test_client.post("/delete", data=data)
        assert response.json() == {"msg": "Index deleted.", "data": index}


def test_search_gpt():
    index = "193b3d9c-744c-37d6-bfcb-cc5707cf20d6"
    data = {
        "vendor_id": index,
        "match": {
            "name": "content",
            "search_term": "請您直接回覆「ＯＫ！」即可，不用多說什麼。",
            "operator": "OR",
            "min_should_match": 1
        },
        "strict": False
    }
    json_data = json.dumps(data)
    response = test_client.post("/search-gpt", data=json_data)

    assert response.json()["msg"] == "Document(s) found!"


def test_search():
    index = "193b3d9c-744c-37d6-bfcb-cc5707cf20d6"
    data = {
        "vendor_id": index,
        "match": {
            "name": "content",
            "search_term": "請您直接回覆「ＯＫ！」即可，不用多說什麼。",
            "operator": "OR",
            "min_should_match": 1
        }
    }
    json_data = json.dumps(data)
    response = test_client.post("/search", data=json_data)

    assert response.json()["msg"] == "Document(s) found!"

    data["match"]["search_term"] = "ㄎㄎ"
    json_data = json.dumps(data)
    response = test_client.post("/search", data=json_data)

    assert response.status_code == 204
