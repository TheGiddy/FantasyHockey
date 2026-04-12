"""Parquet-backed local cache so we don't re-hit APIs on every run.

Each cached item is stored as ``{cache_dir}/{key}.parquet``.  The *key* is
a filesystem-safe slug derived from the endpoint name and season.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from fantasy_hockey.config import CACHE_DIR


def _slugify(text: str) -> str:
    """Turn an arbitrary key like 'skater_summary_20242025' into a safe filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)


def cache_path(key: str) -> Path:
    return CACHE_DIR / f"{_slugify(key)}.parquet"


def has(key: str) -> bool:
    return cache_path(key).exists()


def load(key: str) -> pd.DataFrame:
    return pd.read_parquet(cache_path(key))


def save(key: str, df: pd.DataFrame) -> Path:
    path = cache_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def load_or_fetch(
    key: str,
    fetch_fn: callable,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Return cached dataframe if available, otherwise call *fetch_fn* and cache the result."""
    if not force and has(key):
        return load(key)
    df = fetch_fn()
    save(key, df)
    return df
