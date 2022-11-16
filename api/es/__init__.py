import os

ELASTIC_IP = os.environ["ELASTIC_SERVER"]
ELASTIC_PORT = int(os.environ["ELASTIC_PORT"])

KNOWN_INDEXES = {
    "tiip-test": {"context": "a"}
}
