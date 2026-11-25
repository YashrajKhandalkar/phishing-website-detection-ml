"""Print the model-comparison results as a Markdown table for the README.

Run after ``python src/train_model.py``. The numbers come straight from
``artifacts/model_comparison.csv`` so nothing is typed in by hand.

    python scripts/results_to_markdown.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

COLUMNS = [
    ("model", "Model"),
    ("cv_f1_mean", "CV F1 (mean)"),
    ("test_accuracy", "Test accuracy"),
    ("test_precision_phishing", "Precision (phishing)"),
    ("test_recall_phishing", "Recall (phishing)"),
    ("test_f1_phishing", "F1 (phishing)"),
    ("test_roc_auc", "ROC-AUC"),
]


def main() -> int:
    csv_path = ARTIFACTS / "model_comparison.csv"
    if not csv_path.exists():
        print("artifacts/model_comparison.csv not found. Run `python src/train_model.py` first.", file=sys.stderr)
        return 1

    best = ""
    meta_path = ARTIFACTS / "model_metadata.json"
    if meta_path.exists():
        best = json.loads(meta_path.read_text(encoding="utf-8")).get("best_model", "")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    print("| " + " | ".join(label for _, label in COLUMNS) + " |")
    print("|" + "|".join(["---"] + ["---:"] * (len(COLUMNS) - 1)) + "|")
    for row in rows:
        cells = []
        for key, _ in COLUMNS:
            value = row.get(key, "")
            if key == "model":
                cells.append(f"**{value}** (selected)" if value == best else value)
            else:
                cells.append(f"{float(value):.4f}" if value not in ("", None) else "-")
        print("| " + " | ".join(cells) + " |")
    print("\nTest metrics are computed on a hostname-disjoint hold-out split (see README, Evaluation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
