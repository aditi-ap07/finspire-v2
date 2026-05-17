from utils.config import DB_PATH

import streamlit as st
import sqlite3


@st.cache_resource(show_spinner=False)
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS runs(
        run_id TEXT PRIMARY KEY,
        ts_ist TEXT,
        batch_latency REAL,
        per_headline_latency REAL,
        n_items INTEGER,
        alpha REAL,
        pos_thr REAL,
        neg_thr REAL,
        finbert_model TEXT,
        vader_version TEXT
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS news_raw(
        uid TEXT PRIMARY KEY,
        symbol TEXT,
        title TEXT,
        link TEXT,
        source TEXT,
        published_dt TEXT
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS news_scores(
        uid TEXT PRIMARY KEY,
        score_vader REAL,
        score_finbert REAL,
        score_fused REAL,
        label TEXT,
        engines TEXT,
        run_id TEXT,
        FOREIGN KEY(uid) REFERENCES news_raw(uid)
    )""")

    conn.commit()
    return conn
