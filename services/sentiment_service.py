from datetime import datetime, timedelta
from utils.config import IST, POS_THR_DEFAULT, NEG_THR_DEFAULT, ADAPTIVE_MIN_COUNT
import pandas as pd
from typing import List, Optional
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def score_vader(text: str, analyzer: SentimentIntensityAnalyzer) -> float:
    try:
        return float(analyzer.polarity_scores(text or "")["compound"])
    except Exception:
        return 0.0


def finbert_scores_batch(texts: List[str], finbert) -> List[Optional[float]]:
    if finbert is None:
        return [None] * len(texts)

    try:
        outs = finbert(texts, truncation=True)
        scores = []

        for out in outs:
            if isinstance(out, dict) and "label" in out:
                label = out["label"].lower()
                sc = float(out.get("score", 0.0))

                if label == "positive":
                    scores.append(sc)
                elif label == "negative":
                    scores.append(-sc)
                else:
                    scores.append(0.0)
            else:
                d = {o["label"].lower(): float(o["score"]) for o in out}
                p_pos = d.get("positive", 0.0)
                p_neg = d.get("negative", 0.0)
                scores.append(p_pos - p_neg)

        return scores

    except Exception:
        return [None] * len(texts)


def label_for_score(s: float, pos: float, neg: float) -> str:
    if s >= pos:
        return "Positive"
    if s <= neg:
        return "Negative"
    return "Neutral"


def compute_alpha(df: pd.DataFrame) -> Optional[float]:
    if "score_finbert" not in df.columns or "score_vader" not in df.columns:
        return None

    has_both = df["score_finbert"].notna()
    if not has_both.any():
        return None

    def sgn(x):
        return 1 if x > 0 else (-1 if x < 0 else 0)

    agree = (
        df.loc[has_both, "score_finbert"].apply(sgn)
        == df.loc[has_both, "score_vader"].apply(sgn)
    )

    return float(agree.mean())


def compute_adaptive_thresholds(df: pd.DataFrame):
    now_ist = datetime.now(IST)

    df["_dt"] = pd.to_datetime(df["published_dt"], errors="coerce")
    recent = df[df["_dt"] >= (now_ist - timedelta(hours=24))]

    pos_thr, neg_thr = POS_THR_DEFAULT, NEG_THR_DEFAULT

    if len(recent) >= ADAPTIVE_MIN_COUNT:
        try:
            q67 = float(recent["score_fused"].quantile(0.67))
            q33 = float(recent["score_fused"].quantile(0.33))

            pos_thr = max(q67, 0.10)
            neg_thr = min(q33, -0.10)
        except Exception:
            pos_thr, neg_thr = POS_THR_DEFAULT, NEG_THR_DEFAULT

    return now_ist, pos_thr, neg_thr
