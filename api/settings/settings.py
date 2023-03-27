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
        'travel': [
            ['go', 'head', 'walk', 'move'],
            ['experience', 'live through', 'bear', 'endure', 'undergo'],
            ['eat', 'have a meal', 'consume', 'devour'],
            ['stay at', 'lodging'],
            ['plan', 'plan ahead', 'scheme', 'project'],
            ['look for', 'search', 'check', 'examine', 'explore', 'hunt for']
        ],
        'insurance': [
            ['cover', 'covered by', 'coverage'],
            ['liability', 'credit'],
            ['premium', 'insurance fee', 'insurance price']
        ],
        'admin': [
            ['subsidy', 'monetary aid', 'monetary support'],
            ['application', 'inquiry', 'claim', 'petition', 'form'],
            ['department', 'division', 'unit', 'office'],
            ['money', 'capital', 'cash', 'finances'],
            ['company', 'organization', 'corporation', 'enterprise'],
            ['employee', 'worker', 'laborer', 'representative']
        ]
    },
    "CH": {
        'travel': [
            ['去', '前往', '走', '移動'],
            ['體驗', '撐過', '經驗'],
            ['吃', '吃飯', '進食', '飲食'],
            ['住宿', '飯店', '酒店', '民宿', '住'],
            ['計畫', '規劃', '準備', '安排', '設計'],
            ['尋找', '搜尋', '蒐尋', '搜索']
        ],
        'insurance': [
            ['保險範圍內', '保險內', '保險內含'],
            ['信用', '負債', '虧空'],
            ['保險費', '保險費用', '保險月費', '保險年費', '保險價格'],
        ],
        'admin': [
            ['補助', '貨幣補助', '貨幣援助', '貨幣支持'],
            ['申請', '詢問', '要求', '表格', '請願'],
            ['部門', '部署', '單位', '辦公室'],
            ['錢', '本金', '本錢', '款項', '金款', '金錢'],
            ['公司', '企業', '廠商', '組織', '機構'],
            ['員工', '職工', '勞工', '勞動力', '代表人']
        ]
    }
}
