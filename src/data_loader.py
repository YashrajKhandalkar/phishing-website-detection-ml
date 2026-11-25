"""Load the UCI PhiUSIIL dataset and retain only raw URLs plus labels."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_PATH = DATA_DIR / "phiusiil_url_labels.csv"


def _find_column(frame: pd.DataFrame, name: str) -> str:
    matches = [col for col in frame.columns if str(col).strip().lower() == name.lower()]
    if not matches:
        raise ValueError(f"UCI PhiUSIIL data is missing required column: {name}")
    return matches[0]


def _canonical_url_key(raw_url: str) -> str:
    text = str(raw_url).strip()
    if "://" not in text:
        text = "https://" + text.lstrip("/")
    try:
        parsed = urlsplit(text)
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            return text.strip().lower()
        port = parsed.port
        netloc = host
        if port is not None:
            netloc += f":{port}"
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))
    except ValueError:
        return text.strip()


def load_url_dataset(force_refresh: bool = False) -> tuple[pd.Series, pd.Series, dict]:
    """Return (URL strings, phishing labels 0/1, provenance).

    UCI label convention: 1 = legitimate, 0 = phishing. This function converts
    it to the project's convention: 1 = phishing, 0 = legitimate.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    source = "Local cached URL/label extract from UCI PhiUSIIL dataset"
    if CACHE_PATH.exists() and not force_refresh:
        cached = pd.read_csv(CACHE_PATH)
        url_col = next((c for c in cached.columns if str(c).strip().lower() in {"url", "website_url"}), None)
        label_col = next((c for c in cached.columns if str(c).strip().lower() in {"uci_label", "label", "result"}), None)
        if url_col is None or label_col is None:
            raise ValueError("The local PhiUSIIL cache must contain URL and label/uci_label columns.")
        data = pd.DataFrame({"url": cached[url_col], "uci_label": cached[label_col]})
    else:
        try:
            from ucimlrepo import fetch_ucirepo
            dataset = fetch_ucirepo(id=967)
            feature_frame = dataset.data.features
            target_frame = dataset.data.targets
            url_column = _find_column(feature_frame, "URL")
            label_column = _find_column(target_frame, "label") if any(
                str(c).strip().lower() == "label" for c in target_frame.columns
            ) else target_frame.columns[0]
            data = pd.DataFrame({
                "url": feature_frame[url_column].astype(str),
                "uci_label": pd.to_numeric(target_frame[label_column], errors="coerce"),
            })
            source = "UCI Machine Learning Repository, PhiUSIIL Phishing URL dataset (ID 967)"
            data.to_csv(CACHE_PATH, index=False)
        except Exception as exc:
            raise RuntimeError(
                "Could not download UCI dataset 967. Connect to the internet and rerun, "
                "or download the official PhiUSIIL CSV from the UCI dataset page and "
                "save it as data/phiusiil_url_labels.csv (the loader reads its URL and label columns). "
                f"Original error: {exc}"
            ) from exc

    raw_record_count = int(len(data))
    data = data.dropna(subset=["url", "uci_label"]).copy()
    data["url"] = data["url"].astype(str).str.strip()
    data["uci_label"] = pd.to_numeric(data["uci_label"], errors="coerce")
    data = data.dropna(subset=["uci_label"])
    allowed = set(data["uci_label"].astype(int).unique().tolist())
    if not allowed.issubset({0, 1}) or len(allowed) != 2:
        raise ValueError(f"Unexpected UCI label values: {sorted(allowed)}; expected 0 and 1.")
    data = data[data["url"].ne("")].copy()
    # Normalize only for duplicate detection; preserve original URL text for extraction.
    data["url_key"] = data["url"].map(_canonical_url_key)
    before = len(data)
    data = data.drop_duplicates(subset=["url_key", "uci_label"], keep="first").drop(columns="url_key")
    duplicates_removed = before - len(data)
    # If an identical normalized URL has conflicting labels, discard it rather
    # than allowing the same URL to leak across the train/test partitions.
    norm_key = data["url"].map(_canonical_url_key)
    conflict_counts = data.assign(_key=norm_key).groupby("_key")["uci_label"].nunique()
    conflicts = set(conflict_counts[conflict_counts > 1].index)
    conflicting_rows_removed = int(norm_key.isin(conflicts).sum()) if conflicts else 0
    if conflicts:
        data = data.loc[~norm_key.isin(conflicts)].copy()

    urls = data["url"].reset_index(drop=True)
    # UCI: 0 phishing, 1 legitimate. Project: 1 phishing, 0 legitimate.
    y = (1 - data["uci_label"].astype(int)).astype(int).reset_index(drop=True)
    provenance = {
        "dataset_name": "PhiUSIIL Phishing URL (Website)",
        "uci_dataset_id": 967,
        "source": source,
        "uci_original_records": raw_record_count,
        "records_loaded": int(len(urls)),
        "duplicates_removed": int(duplicates_removed),
        "conflicting_url_groups_removed": int(len(conflicts)),
        "conflicting_url_rows_removed": conflicting_rows_removed,
        "label_mapping": {"uci_0": "phishing (1)", "uci_1": "legitimate (0)"},
        "class_counts": {
            "legitimate_0": int((y == 0).sum()),
            "phishing_1": int((y == 1).sum()),
        },
        "license": "CC BY 4.0",
        "citation": "Prasad, A. & Chandra, S. (2024). PhiUSIIL Phishing URL (Website). UCI Machine Learning Repository. https://doi.org/10.1016/j.cose.2023.103545.",
    }
    return urls, y, provenance
