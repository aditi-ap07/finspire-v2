from zoneinfo import ZoneInfo
from typing import Dict, List

import os

IST = ZoneInfo("Asia/Kolkata")

DB_PATH = os.environ.get("DB_PATH", "data/finspire.sqlite3")

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

W_F, W_V = 0.7, 0.3
POS_THR_DEFAULT, NEG_THR_DEFAULT = 0.15, -0.15
ADAPTIVE_MIN_COUNT = 50
