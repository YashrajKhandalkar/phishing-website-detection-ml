"""Offline tests for dataset cleaning and the UCI -> project label mapping."""
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd

from src import data_loader


def _load(rows):
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "cache.csv"
        pd.DataFrame(rows, columns=["url", "label"]).to_csv(cache, index=False)
        with mock.patch.object(data_loader, "DATA_DIR", Path(tmp)), \
                mock.patch.object(data_loader, "CACHE_PATH", cache):
            return data_loader.load_url_dataset()


def test_labels_are_inverted_to_project_convention():
    urls, y, meta = _load([
        ("https://legit.example.com/", 1),      # UCI 1 = legitimate -> project 0
        ("https://phish.example.net/login", 0),  # UCI 0 = phishing   -> project 1
    ])
    mapping = dict(zip(urls, y))
    assert mapping["https://legit.example.com/"] == 0
    assert mapping["https://phish.example.net/login"] == 1
    assert meta["class_counts"] == {"legitimate_0": 1, "phishing_1": 1}


def test_duplicates_and_conflicting_labels_are_removed():
    urls, y, meta = _load([
        ("https://a.example.com/x", 1),
        ("https://a.example.com/x/", 1),   # same normalized URL -> duplicate
        ("https://b.example.com/", 0),
        ("https://b.example.com/", 1),     # same URL, conflicting labels -> dropped
        ("https://c.example.com/", 0),
    ])
    assert sorted(urls) == ["https://a.example.com/x", "https://c.example.com/"]
    assert meta["duplicates_removed"] == 1
    assert meta["conflicting_url_groups_removed"] == 1
