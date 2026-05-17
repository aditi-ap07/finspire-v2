from database.repository import db_insert_run, db_upsert_news
from database.db import get_db

from utils.helpers import sentiment_to_emoji, color_for_score
from utils.config import W_F, W_V, DB_PATH

from services.sentiment_service import label_for_score, finbert_scores_batch, score_vader, compute_alpha, compute_adaptive_thresholds
from services.fetch_service import fetch_headlines_for_symbol
from services.aggregation_service import compute_aggregates

from ui.sidebar import render_sidebar
from ui.components import make_chip

from models.ml_models import get_vader, get_finbert

import pandas as pd
import time
import streamlit as st
import hashlib


def render_page_header():
    st.title("📰 FINSPIRE — Real-Time Market Sentiment (FinBERT + VADER)")
    st.caption(
        "Google News RSS → VADER + FinBERT → Fusion → Aggregates • SQLite persistence • Adaptive thresholds"
    )

    st.markdown('''
    <style>
    .metric-card {border-radius:16px;padding:12px 16px;border:1px solid rgba(0,0,0,0.05);
                  box-shadow:0 2px 8px rgba(0,0,0,0.06);
                  background:linear-gradient(180deg,rgba(255,255,255,0.6),rgba(250,250,250,0.6))}
    .metric-title{font-size:0.85rem;color:#666}
    .metric-value{font-size:1.6rem;font-weight:700}
    .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:0.75rem;background:#111;color:#fff}
    .card{border-radius:14px;padding:12px 14px;margin:6px 0;border-left:6px solid transparent;
          background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.05)}
    .headline-link a {text-decoration:none;}
    </style>
    ''', unsafe_allow_html=True)


def run_app():
    render_page_header()

    symbols, limit, force_vader, min_abs, sentiment_pick, search, ALIASES = render_sidebar()

    vader = get_vader()
    finbert = None if force_vader else get_finbert()
    method_badge = "VADER only" if (
        force_vader or finbert is None) else "FinBERT + VADER (fusion)"

    t0 = time.perf_counter()
    rows = []

    if symbols:
        progress = st.progress(0, text="Fetching headlines…")

        for i, sym in enumerate(symbols):
            items = fetch_headlines_for_symbol(
                sym,
                ALIASES.get(sym, [sym]),
                limit=limit,
                polite_sleep=0.35
            )

            titles = [it["title"] for it in items]
            sf_list = (
                finbert_scores_batch(titles, finbert)
                if finbert is not None
                else [None] * len(items)
            )

            for it, sf in zip(items, sf_list):
                sv = score_vader(it["title"], vader)

                if sf is None:
                    fused = sv
                    engines = "VADER"
                else:
                    fused = W_F * float(sf) + W_V * float(sv)
                    engines = "FinBERT+VADER"

                it.update({
                    "score_vader": sv,
                    "score_finbert": None if sf is None else float(sf),
                    "score_fused": float(max(-1.0, min(1.0, fused))),
                    "engines": engines,
                })

                rows.append(it)

            progress.progress(
                (i + 1) / max(1, len(symbols)),
                text=f"Fetched: {sym}"
            )

        progress.empty()

    df = pd.DataFrame(rows)

    if df.empty:
        st.info(
            "No headlines fetched. Try adding symbols or increasing the per-symbol limit.")
        st.stop()

    df = df.drop_duplicates(subset=["uid"]).reset_index(drop=True)

    now_ist, POS_THR, NEG_THR = compute_adaptive_thresholds(df)

    df["label"] = df["score_fused"].apply(
        lambda s: label_for_score(float(s), POS_THR, NEG_THR)
    )

    df["emoji"] = df["score_fused"].apply(
        lambda s: sentiment_to_emoji(float(s))
    )

    alpha_overall = compute_alpha(df)

    alpha_by_symbol = (
        df.groupby("symbol")
        .apply(lambda x: pd.Series({"alpha": compute_alpha(x)}))
        .reset_index()
    )

    t1 = time.perf_counter()
    batch_latency = t1 - t0
    per_headline_latency = (batch_latency / len(df)) if len(df) else 0.0

    conn = get_db()

    run_id = hashlib.sha256(
        f"{now_ist.isoformat()}|{len(df)}|{batch_latency:.6f}".encode("utf-8")
    ).hexdigest()[:16]

    meta = {
        "run_id": run_id,
        "ts_ist": now_ist.isoformat(),
        "batch_latency": float(batch_latency),
        "per_headline_latency": float(per_headline_latency),
        "n_items": int(len(df)),
        "alpha": None if alpha_overall is None else float(alpha_overall),
        "pos_thr": float(POS_THR),
        "neg_thr": float(NEG_THR),
        "finbert_model": "ProsusAI/finbert" if finbert is not None else "None",
        "vader_version": "vaderSentiment",
    }

    db_insert_run(conn, meta)
    db_upsert_news(conn, df, run_id)

    f = df.copy()

    if min_abs > 0:
        f = f[f["score_fused"].abs() >= min_abs]

    if sentiment_pick != "All":
        f = f[f["label"] == sentiment_pick]

    if search.strip():
        sterm = search.lower().strip()
        f = f[f["title"].str.lower().str.contains(sterm)]

    tab_overview, tab_headlines, tab_symbol, tab_runs = st.tabs(
        ["📊 Overview", "🗞️ Headlines", "📈 By Symbol", "🧾 Runs & Persistence"]
    )

    with tab_overview:
        left, right = st.columns([0.70, 0.30])

        with left:
            st.subheader("Summary")

        with right:
            st.markdown(
                f"<div class='badge'>Scoring: {method_badge}</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='badge'>Bands: +{POS_THR:.2f} / {NEG_THR:.2f}</div>", unsafe_allow_html=True)

            if alpha_overall is not None:
                st.markdown(
                    f"<div class='badge'>α (agreement): {alpha_overall:.3f}</div>", unsafe_allow_html=True)

        agg = compute_aggregates(f)
        cols = st.columns(len(agg) if len(agg) else 1)

        for col, (_, r) in zip(cols, agg.iterrows()):
            with col:
                col.markdown(
                    f"<div class='metric-card'>"
                    f"<div class='metric-title'>{r.symbol} &nbsp; {sentiment_to_emoji(r.mean_score)}</div>"
                    f"<div class='metric-value' style='color:{color_for_score(r.mean_score)}'>{r.mean_score:.3f}</div>"
                    f"<div style='font-size:0.8rem;color:#777'>n={int(r.n)} &nbsp; p95={r.p95:.2f} &nbsp; p05={r.p05:.2f}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown(" ")
        st.write("**Agreement (α) by symbol**")

        st.dataframe(alpha_by_symbol.fillna("—"),
                     width="stretch", hide_index=True)

        st.markdown(" ")
        st.write("**Heat by fused mean score**")

        heat = (
            agg[["symbol", "n", "mean_score"]]
            .set_index("symbol")
            .sort_values("mean_score", ascending=False)
        )

        def style_mean_score(val: float) -> str:
            try:
                v = float(val)
            except Exception:
                v = 0.0
            return f"background-color:{color_for_score(v)}; color:white"

        st.dataframe(
            heat.style
                .format({"mean_score": "{:.3f}"})
                .map(style_mean_score, subset=["mean_score"]),
            width="stretch"
        )

        st.download_button(
            "⬇️ Download summary.csv",
            data=agg.to_csv(index=False).encode("utf-8"),
            file_name="summary.csv",
            mime="text/csv"
        )

    with tab_headlines:
        st.subheader("Headlines")

        sort = st.selectbox(
            "Sort by",
            ["Fused score (desc)", "Fused score (asc)", "Most recent"],
            index=0
        )

        ff = f.copy()

        if sort == "Fused score (desc)":
            ff = ff.sort_values("score_fused", ascending=False)
        elif sort == "Fused score (asc)":
            ff = ff.sort_values("score_fused", ascending=True)
        else:
            ff = ff.sort_values("_dt", ascending=False, na_position="last")

        cards_html = []

        for _, r in ff.iterrows():
            left_color = color_for_score(float(r["score_fused"]))
            chip_sym = make_chip(r["symbol"], color="#fff", bg="#111")
            chip_label = make_chip(r["label"], color="#fff", bg=left_color)

            sv = float(r["score_vader"])
            sf = r["score_finbert"]
            sf_str = "—" if pd.isna(sf) else f"{sf:.3f}"

            card = f"""
            <div class="card" style="border-left-color:{left_color}">
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px;">
                    {chip_sym} {chip_label}
                    <span style="font-size:0.85rem;color:#777;margin-left:auto;">
                        {r.get("source", "") or ""}
                    </span>
                </div>

                <div style="font-weight:600;margin-bottom:4px;">
                    <a href="{r["link"]}" target="_blank" style="text-decoration:none;color:#0b66c3;">
                        {r["title"]}
                    </a>
                </div>

                <div style="font-size:0.85rem;color:#666;">
                    {r["emoji"]} fused: {r["score_fused"]:.3f} |
                    FinBERT: {sf_str} |
                    VADER: {sv:.3f} |
                    {r["published_dt"]}
                </div>
            </div>
            """

            cards_html.append(card)

        if not cards_html:
            st.info("No headlines match the current filters.")
        else:
            st.markdown("\n".join(cards_html), unsafe_allow_html=True)

        st.download_button(
            "⬇️ Download headlines.csv",
            data=ff.drop(columns=["_dt"]).to_csv(index=False).encode("utf-8"),
            file_name="headlines.csv",
            mime="text/csv"
        )

    with tab_symbol:
        st.subheader("Per-Symbol Drilldown (Fused)")

        sel = st.selectbox(
            "Select symbol", options=sorted(df["symbol"].unique()))

        sub = f[f["symbol"] == sel].copy().sort_values(
            "score_fused", ascending=False)

        if sub.empty:
            st.info("No headlines for this symbol under current filters.")
        else:
            pos = sub[sub["label"] == "Positive"].head(5)
            neu = sub[sub["label"] == "Neutral"].head(5)
            neg = sub[sub["label"] == "Negative"].sort_values(
                "score_fused").head(5)

            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown("**Top Positive**")
                if pos.empty:
                    st.write("–")
                for _, r in pos.iterrows():
                    st.markdown(
                        f"- {r['emoji']} **{r['score_fused']:.3f}** — [{r['title']}]({r['link']})")

            with c2:
                st.markdown("**Neutral**")
                if neu.empty:
                    st.write("–")
                for _, r in neu.iterrows():
                    st.markdown(
                        f"- {r['emoji']} **{r['score_fused']:.3f}** — [{r['title']}]({r['link']})")

            with c3:
                st.markdown("**Top Negative**")
                if neg.empty:
                    st.write("–")
                for _, r in neg.iterrows():
                    st.markdown(
                        f"- {r['emoji']} **{r['score_fused']:.3f}** — [{r['title']}]({r['link']})")

            st.markdown("---")
            st.markdown("**Full list (with engines)**")

            sub["headline"] = sub.apply(
                lambda r: f"<a href='{r['link']}' target='_blank'>{r['title']}</a>",
                axis=1
            )

            view_cols = [
                "emoji", "score_fused", "score_finbert", "score_vader",
                "label", "source", "published_dt", "engines", "headline"
            ]

            st.write(sub[view_cols].to_html(escape=False,
                                            index=False), unsafe_allow_html=True)

    with tab_runs:
        st.subheader("Run metadata & persistence")

        st.write(f"**DB Path**: `{DB_PATH}`")
        st.write(f"**Current run_id**: `{run_id}`")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Batch latency (s)", f"{batch_latency:.2f}")
        c2.metric("Per-headline (ms)", f"{per_headline_latency * 1000:.1f}")
        c3.metric("Items processed", f"{len(df)}")
        c4.metric("Agreement α",
                  f"{alpha_overall:.3f}" if alpha_overall is not None else "—")

        try:
            runs_df = pd.read_sql_query(
                "SELECT * FROM runs ORDER BY ts_ist DESC LIMIT 15",
                conn
            )

            st.write("**Recent runs**")
            st.dataframe(runs_df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.warning(f"Could not query runs: {e}")
