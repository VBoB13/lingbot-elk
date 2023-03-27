import os
from pathlib import Path

from helpers.helpers import get_local_ip

BASE_DIR = os.getcwd()

# API dir's
LOG_DIR = os.path.join(BASE_DIR, "log")
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_DIR = os.path.join(DATA_DIR, "csv")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
CSV_FINISHED_DIR = os.path.join(CSV_DIR, 'finished')
TIIP_PDF_DIR = os.path.join(DATA_DIR, "tiip", "pdf")
TIIP_CSV_DIR = os.path.join(DATA_DIR, "tiip", "csv")
TIIP_DOC_DIR = os.path.join(DATA_DIR, "tiip", "docs")

# OpenAI stuff
GPT3_SERVER = get_local_ip(os.environ.get("GPT3_SERVER", "0.0.0.0"))
GPT3_PORT = int(os.environ.get("GPT3_PORT", "4200"))

# Dictionairy dir's (ELK)
path = Path(BASE_DIR)
parent_dir = path.parent.absolute()
DIC_DIR = os.path.join(parent_dir, 'elk', 'elasticsearch',
                       'elasticsearch-analysis-ik-8.3.3', 'config')
DIC_FILE = os.path.join(DIC_DIR, 'extra_main.dic')

# Servers
CLAUDES_SERVER = "192.168.1.132"
CLAUDES_PORT = 8000

# BASE VARS
SYNONYM_BASES: dict[str, dict[str, list]] = {
    "EN": {
        'travel': ['go', 'experience', 'eat', 'stay at', 'plan']
    }
}

# Constants
SYNONYM_WORDS: dict[str, dict[str, list[list[str]]]] = {
    "EN": {
        'travel': [['go', 'head', 'walk', 'move'], ['experience', 'live through', 'bear', 'endure', 'undergo'], ['eat', 'have a meal', 'consume', 'devour'], ['stay at', 'lodging'], ['plan', 'plan ahead', 'scheme', 'project'], ['look for', 'search', 'check', 'examine', 'explore', 'hunt for']],
        'insurance': ['cover', 'liability', 'credit', 'premium'],
        'admin': ['subsidy', 'application', 'department', 'money', 'company', 'employee']
    },
    "CH": {
        'travel': ['去', '體驗', '吃', '住宿', '計畫', '尋找'],
        'insurance': ['保險範圍內', '信用', '保險費', '虧空'],
        'admin': ['申請', '補助', '部門', '錢', '公司', '員工']
    }
}
