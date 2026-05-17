import pandas as pd


def db_upsert_news(conn, df_rows: pd.DataFrame, run_id: str):
    if df_rows.empty:
        return

    cur = conn.cursor()

    # raw
    raw_cols = ["uid", "symbol", "title", "link", "source", "published_dt"]
    for r in df_rows[raw_cols].itertuples(index=False):
        cur.execute("""
        INSERT OR IGNORE INTO news_raw(uid, symbol, title, link, source, published_dt)
        VALUES(?,?,?,?,?,?)
        """, tuple(r))

    # scores
    score_cols = ["uid", "score_vader", "score_finbert",
                  "score_fused", "label", "engines"]
    for r in df_rows[score_cols].itertuples(index=False):
        cur.execute("""
        INSERT INTO news_scores(uid, score_vader, score_finbert, score_fused, label, engines, run_id)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(uid) DO UPDATE SET
          score_vader=excluded.score_vader,
          score_finbert=excluded.score_finbert,
          score_fused=excluded.score_fused,
          label=excluded.label,
          engines=excluded.engines,
          run_id=excluded.run_id
        """, (*tuple(r), run_id))

    conn.commit()


def db_insert_run(conn, meta: dict):
    conn.execute("""
    INSERT INTO runs(
        run_id, ts_ist, batch_latency, per_headline_latency,
        n_items, alpha, pos_thr, neg_thr,
        finbert_model, vader_version
    )
    VALUES(
        :run_id, :ts_ist, :batch_latency, :per_headline_latency,
        :n_items, :alpha, :pos_thr, :neg_thr,
        :finbert_model, :vader_version
    )
    """, meta)
    conn.commit()
