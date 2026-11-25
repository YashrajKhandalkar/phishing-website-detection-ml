"""Train URL-first phishing classifiers from the UCI PhiUSIIL URL dataset."""
from __future__ import annotations

from pathlib import Path
import json
import warnings
import sys

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report,
)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import GaussianNB
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ARTIFACTS = ROOT / "artifacts"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
RANDOM_STATE = 42

from src.data_loader import load_url_dataset
from src.url_features import FEATURE_NAMES, extract_url_features, normalize_user_url


def _host_group(url: str) -> str:
    """Approximate registrable host key for grouped splitting (no network call)."""
    from urllib.parse import urlsplit
    raw = str(url).strip()
    if "://" not in raw:
        raw = "https://" + raw.lstrip("/")
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").lower().strip(".")
    except ValueError:
        host = "__invalid__"
    return host or "__invalid__"


def build_models():
    """Four classical classifiers matching the course project's suggested family."""
    return {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                max_iter=2000, class_weight="balanced", solver="lbfgs", random_state=RANDOM_STATE
            )),
        ]),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=18, min_samples_leaf=5, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Support Vector Machine (Linear SVM)": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LinearSVC(
                C=0.5, class_weight="balanced", dual="auto", max_iter=6000, random_state=RANDOM_STATE
            )),
        ]),
        "Gaussian Naive Bayes": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", GaussianNB()),
        ]),
    }


def _positive_scores(model, X):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, list(model.classes_).index(1)]
    return model.decision_function(X)


def _evaluate(model, X_test, y_test):
    pred = model.predict(X_test)
    scores = _positive_scores(model, X_test)
    return {
        "test_accuracy": float(accuracy_score(y_test, pred)),
        "test_precision_phishing": float(precision_score(y_test, pred, zero_division=0)),
        "test_recall_phishing": float(recall_score(y_test, pred, zero_division=0)),
        "test_f1_phishing": float(f1_score(y_test, pred, zero_division=0)),
        "test_roc_auc": float(roc_auc_score(y_test, scores)),
    }, pred, scores


def main():
    warnings.filterwarnings("ignore", category=UserWarning)
    for path in (ARTIFACTS, REPORTS, FIGURES):
        path.mkdir(parents=True, exist_ok=True)

    print("Loading UCI PhiUSIIL URL dataset (ID 967)...")
    urls, y, provenance = load_url_dataset()
    print(f"Loaded {len(urls):,} unique URL records. Extracting URL features...")

    feature_rows = []
    valid_positions = []
    for idx, raw_url in enumerate(urls.tolist()):
        try:
            normalized_url = normalize_user_url(raw_url)
            feature_rows.append(extract_url_features(normalized_url))
            valid_positions.append(idx)
        except Exception:
            # Invalid URLs cannot be represented consistently at inference time.
            continue
        if (idx + 1) % 25000 == 0:
            print(f"  Processed {idx + 1:,}/{len(urls):,} URLs")

    if len(valid_positions) < 1000:
        raise RuntimeError("Too few valid URLs remained after feature extraction; check the UCI download.")
    provenance["records_after_url_validation"] = int(len(valid_positions))
    provenance["invalid_urls_skipped"] = int(len(urls) - len(valid_positions))
    X = pd.DataFrame(feature_rows, columns=FEATURE_NAMES).astype(float)
    y = y.iloc[valid_positions].reset_index(drop=True)
    valid_urls = urls.iloc[valid_positions].reset_index(drop=True)
    groups = pd.Series([_host_group(url) for url in valid_urls], name="host_group")

    if not set(np.unique(y)).issubset({0, 1}) or y.nunique() != 2:
        raise ValueError("Binary target required: 0=legitimate, 1=phishing.")
    if X.isna().any().any() or not np.isfinite(X.to_numpy()).all():
        raise ValueError("URL feature extraction produced missing or non-finite values.")

    # Keep all URLs from an exact host in only one partition to reduce host-level leakage.
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    groups_train = groups.iloc[train_idx]
    overlap = set(groups.iloc[train_idx]).intersection(set(groups.iloc[test_idx]))
    if overlap:
        raise RuntimeError("Host-group leakage detected between train and test partitions.")

    models = build_models()
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE + 1)
    rows = []
    fitted_models = {}
    for name, estimator in models.items():
        print(f"Cross-validating {name}...")
        cv_scores = cross_val_score(
            estimator, X_train, y_train, cv=cv, groups=groups_train,
            scoring="f1", n_jobs=-1, error_score="raise",
        )
        print(f"  CV F1: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
        fitted = clone(estimator).fit(X_train, y_train)
        metrics, predictions, scores = _evaluate(fitted, X_test, y_test)
        fitted_models[name] = fitted
        rows.append({
            "model": name,
            "cv_f1_mean": float(cv_scores.mean()),
            "cv_f1_std": float(cv_scores.std()),
            **metrics,
        })

    comparison = pd.DataFrame(rows).sort_values("cv_f1_mean", ascending=False).reset_index(drop=True)
    best_name = str(comparison.loc[0, "model"])
    final_model = fitted_models[best_name]

    # Calibrate the linear SVM so the app can show a model-estimated score.
    # The score is not a guarantee and must not be interpreted as a security verdict.
    if best_name == "Support Vector Machine (Linear SVM)":
        print("Calibrating the selected SVM score for display...")
        final_model = CalibratedClassifierCV(
            estimator=clone(models[best_name]), method="sigmoid", cv=3, n_jobs=-1
        ).fit(X_train, y_train)

    best_metrics, best_predictions, best_scores = _evaluate(final_model, X_test, y_test)
    for key, value in best_metrics.items():
        comparison.loc[comparison["model"] == best_name, key] = value
    comparison.to_csv(ARTIFACTS / "model_comparison.csv", index=False)

    cm = confusion_matrix(y_test, best_predictions, labels=[0, 1])
    pd.DataFrame(
        cm,
        index=["Actual Legitimate", "Actual Phishing"],
        columns=["Predicted Legitimate", "Predicted Phishing"],
    ).to_csv(ARTIFACTS / "confusion_matrix.csv")

    report_text = classification_report(
        y_test, best_predictions, labels=[0, 1], target_names=["Legitimate", "Phishing"], zero_division=0
    )
    (ARTIFACTS / "classification_report.txt").write_text(report_text, encoding="utf-8")

    errors = pd.DataFrame({
        "test_position": np.arange(len(y_test)),
        "actual_is_phishing": y_test.to_numpy(),
        "predicted_is_phishing": best_predictions,
        "error_type": np.where(
            (y_test.to_numpy() == 1) & (best_predictions == 0), "False Negative (phishing missed)",
            np.where((y_test.to_numpy() == 0) & (best_predictions == 1), "False Positive (legitimate flagged)", "Correct")
        ),
    })
    errors = errors.loc[errors["error_type"] != "Correct"]
    errors.to_csv(ARTIFACTS / "error_analysis.csv", index=False)

    # Permutation importance on a bounded random test sample for practical runtime.
    imp_n = min(2500, len(X_test))
    X_imp = X_test.sample(n=imp_n, random_state=RANDOM_STATE)
    y_imp = y_test.loc[X_imp.index]
    perm = permutation_importance(
        final_model, X_imp, y_imp, scoring="f1", n_repeats=3,
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    importance = pd.DataFrame({
        "feature": FEATURE_NAMES,
        "importance_mean": perm.importances_mean,
        "importance_std": perm.importances_std,
    }).sort_values("importance_mean", ascending=False)
    importance.to_csv(ARTIFACTS / "feature_importance.csv", index=False)

    # Figures
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Legitimate", "Phishing"],
                yticklabels=["Legitimate", "Phishing"], ax=ax)
    ax.set_title("Confusion Matrix - Selected URL Model")
    ax.set_xlabel("Predicted label"); ax.set_ylabel("Actual label")
    fig.tight_layout(); fig.savefig(FIGURES / "confusion_matrix.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    plot_data = comparison.sort_values("test_f1_phishing", ascending=True)
    ax.barh(plot_data["model"], plot_data["test_f1_phishing"])
    ax.set_xlim(0, 1); ax.set_xlabel("Test F1-score"); ax.set_title("Classifier Comparison")
    fig.tight_layout(); fig.savefig(FIGURES / "model_comparison.png", dpi=160); plt.close(fig)

    top_imp = importance.head(12).sort_values("importance_mean", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top_imp["feature"], top_imp["importance_mean"], xerr=top_imp["importance_std"])
    ax.set_xlabel("Mean F1 decrease after permutation"); ax.set_title("URL Feature Importance")
    fig.tight_layout(); fig.savefig(FIGURES / "feature_importance.png", dpi=160); plt.close(fig)

    joblib.dump(final_model, ARTIFACTS / "best_url_model.joblib")
    metadata = {
        **provenance,
        "feature_count": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "best_model": best_name,
        "selection_method": "Highest mean 5-fold stratified group cross-validation F1-score on training hosts",
        "split_strategy": "80:20 approximately, stratified group split by URL hostname; no hostname overlap between train and test",
        "random_state": RANDOM_STATE,
        "train_records": int(len(X_train)),
        "test_records": int(len(X_test)),
        "train_unique_hosts": int(groups_train.nunique()),
        "test_unique_hosts": int(groups.iloc[test_idx].nunique()),
        "class_counts_after_cleaning": {
            "legitimate_0": int((y == 0).sum()),
            "phishing_1": int((y == 1).sum()),
        },
        "positive_class": "Phishing (1)",
        "prediction_input": "A raw website URL string; URL-only features are generated locally.",
        "page_inspection": "Optional, separate, best-effort HTTP/HTML inspection; its indicators are not fed into the ML classifier.",
        "warning": "Educational decision-support only. Model scores are not guarantees and must not be the sole basis for security decisions.",
    }
    (ARTIFACTS / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("\nTraining complete.")
    print(comparison.to_string(index=False))
    print(f"\nSelected model: {best_name}")
    print(f"Train rows: {len(X_train):,} | Test rows: {len(X_test):,}")
    print(f"Host groups: train={groups_train.nunique():,}, test={groups.iloc[test_idx].nunique():,}")
    print(f"Artifacts saved to: {ARTIFACTS}")
    print("Next: python generate_report.py && streamlit run app.py")


if __name__ == "__main__":
    main()
