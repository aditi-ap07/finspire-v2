from utils.company_loader import load_companies, generate_aliases

import time
import streamlit as st
import pandas as pd


def render_sidebar():
    with st.sidebar:
        st.header("Controls")

        df = load_companies()

        # ───── Company Search ─────
        query = st.text_input("Search company")

        query_clean = query.strip().lower()

        def matches(row):
            symbol = str(row["symbol"]).lower()
            name = str(row["name"]).lower()

            aliases = generate_aliases(row["symbol"], row["name"])
            aliases = [a.lower() for a in aliases]

            return (
                query_clean in symbol or
                query_clean in name or
                any(query_clean in a for a in aliases)
            )

        if query_clean:
            matches_df = df[df.apply(matches, axis=1)]
        else:
            matches_df = df

        selected_names = st.multiselect(
            "Select companies",
            options=matches_df["name"].tolist()
        )

        # ───── Build alias dict ─────
        aliases_dict = {}

        for name in selected_names:
            row = df[df["name"] == name].iloc[0]
            symbol = row["symbol"]
            aliases_dict[symbol] = generate_aliases(symbol, name)

        # ───── Controls ─────
        limit = st.slider("Headlines per symbol", 5, 50, 20, step=5)

        force_vader = st.checkbox(
            "Force VADER only (skip FinBERT)", value=False)

        min_abs = st.slider("Min abs(fused score) filter", 0.0, 1.0, 0.0, 0.05)

        sentiment_pick = st.radio(
            "Show",
            ["All", "Positive", "Neutral", "Negative"],
            horizontal=True
        )

        search = st.text_input("Search term (in title)", "")

        if st.button("🔄 Refresh now"):
            st.query_params["_"] = str(time.time())

        # ───── Debug view (optional) ─────
        if aliases_dict:
            with st.expander("Selected Aliases (debug)"):
                st.dataframe(
                    pd.DataFrame([
                        {"symbol": k, "aliases": "; ".join(v)}
                        for k, v in aliases_dict.items()
                    ]),
                    width="stretch",
                    hide_index=True
                )

    return selected_names, limit, force_vader, min_abs, sentiment_pick, search, aliases_dict
