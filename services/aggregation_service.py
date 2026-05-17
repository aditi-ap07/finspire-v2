import pandas as pd


def compute_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("symbol")
          .agg(
              n=("title", "count"),
              mean_score=("score_fused", "mean"),
              p95=("score_fused", lambda s: s.quantile(0.95)),
              p05=("score_fused", lambda s: s.quantile(0.05)),
        )
        .reset_index()
        .sort_values("mean_score", ascending=False)
    )
