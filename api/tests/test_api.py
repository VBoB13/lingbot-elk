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
