from utils.helpers import row_uid, to_ist_iso
from utils.config import GOOGLE_NEWS_RSS

from typing import List
import streamlit as st
from urllib.parse import quote_plus
import feedparser
import time


def build_query(aliases: list[str]) -> str:
    terms = [f'"{a}"' if " " in a else a for a in aliases]
    q = " OR ".join(terms)
    return quote_plus(q, safe="")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_headlines_for_symbol(
    symbol: str,
    aliases: List[str],
    limit: int = 20,
    polite_sleep: float = 0.5
):
    url = GOOGLE_NEWS_RSS.format(query=build_query(aliases))
    d = feedparser.parse(url)

    time.sleep(polite_sleep)

    entries = d.entries[:limit] if limit else d.entries
    items = []

    for e in entries:
        title = getattr(e, "title", "")
        link = getattr(e, "link", "")
        pub_str = getattr(e, "published", "")

        it = {
            "uid": row_uid(title, link),
            "symbol": symbol,
            "title": title,
            "link": link,
            "published": pub_str,
            "published_dt": to_ist_iso(pub_str),
            "source": getattr(e, "source", {}).get(
                "title", getattr(e, "source", "")
            ) if hasattr(e, "source") else "",
        }

        items.append(it)

    return items
