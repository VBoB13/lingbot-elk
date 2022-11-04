import os

ELASTIC_HOST = "{}:{}".format(
    os.environ["ELASTIC_SERVER"], os.environ["ELASTIC_PORT"])
