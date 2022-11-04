import os

ELASTIC_HOST = "{}:{}".format(
    os.environ["ELASTIC_HOST"], os.environ["ELASTIC_PORT"])
