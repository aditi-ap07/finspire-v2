import streamlit as st
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def _load_finbert_pipeline():
    try:
        from transformers import pipeline

        return pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,
            truncation=True
        )

    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def get_vader() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


@st.cache_resource(show_spinner=False)
def get_finbert():
    return _load_finbert_pipeline()
