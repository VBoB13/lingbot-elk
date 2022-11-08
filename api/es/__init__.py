import os

ELASTIC_HOST = "{}:{}".format(
    os.environ["API_SERVER"], os.environ["API_PORT"])
