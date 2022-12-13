import os
from pathlib import Path

BASE_DIR = os.getcwd()

# API dir's
LOG_DIR = os.path.join(BASE_DIR, "log")
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_DIR = os.path.join(DATA_DIR, 'csv')
CSV_FINISHED_DIR = os.path.join(CSV_DIR, 'finished')
TIIP_PDF_DIR = os.path.join(DATA_DIR, "tiip", "pdf")
TIIP_CSV_DIR = os.path.join(DATA_DIR, "tiip", "csv")

# OpenAI stuff
GPT3_SERVER = os.environ.get("GPT3_SERVER", "192.168.112.3")
GPT3_PORT = int(os.environ.get("GPT3_PORT", "4200"))

# Dictionairy dir's (ELK)
path = Path(BASE_DIR)
parent_dir = path.parent.absolute()
DIC_DIR = os.path.join(parent_dir, 'elk', 'elasticsearch',
                       'elasticsearch-analysis-ik-8.3.3', 'config')
DIC_FILE = os.path.join(DIC_DIR, 'extra_main.dic')
