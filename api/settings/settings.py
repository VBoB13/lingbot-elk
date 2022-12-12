import os
from pathlib import Path

from es import ELASTIC_IP

BASE_DIR = os.getcwd()

# API dir's
LOG_DIR = os.path.join(BASE_DIR, "log")
DATA_DIR = os.path.join(BASE_DIR, "data")
TIIP_PDF_DIR = os.path.join(DATA_DIR, "tiip", "pdf")
TIIP_CSV_DIR = os.path.join(DATA_DIR, "tiip", "csv")

# OpenAI stuff
GPT3_SERVER = ELASTIC_IP
GPT3_PORT = int(os.environ.get("GPT3_PORT", "4200"))

# Dictionairy dir's (ELK)
path = Path(BASE_DIR)
parent_dir = path.parent.absolute()
DIC_DIR = os.path.join(parent_dir, 'elk', 'elasticsearch',
                       'elasticsearch-analysis-ik-8.3.3', 'config')
DIC_FILE = os.path.join(DIC_DIR, 'extra_main.dic')
