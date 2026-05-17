import pandas as pd
import re


def load_companies(csv_path: str = "data/companies.csv") -> pd.DataFrame:
    return pd.read_csv(csv_path)


def clean_name(name: str) -> str:
    name = re.sub(r"\b(Ltd|Limited|Ltd\.|Pvt|Private)\b",
                  "", name, flags=re.IGNORECASE)
    return name.strip()


def generate_aliases(symbol: str, name: str):
    base = clean_name(name)

    aliases = {
        symbol,
        name,
        base
    }

    return list(aliases)
