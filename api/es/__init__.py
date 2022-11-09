import os

ELASTIC_IP = str(os.environ["ELASTIC_SERVER"])

ELASTIC_HOST = "http://{}:{}".format(
    ELASTIC_IP, os.environ["ELASTIC_PORT"])
