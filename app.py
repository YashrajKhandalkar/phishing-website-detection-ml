"""URL-first Streamlit interface for phishing URL classification."""
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
import streamlit as st

from src.url_features import FEATURE_NAMES, extract_url_features, normalize_user_url
from src.page_inspector import inspect_public_page

ART = ROOT / "artifacts"
MODEL_PATH = ART / "best_url_model.joblib"
META_PATH = ART / "model_metadata.json"

st.set_page_config(page_title="Phishing URL Detection", page_icon="🛡️", layout="wide")
st.title("🛡️ Phishing Website Detection")
st.caption("URL-first machine-learning analysis with optional, separate webpage inspection")
st.info(
    "The ML model analyzes the URL text and domain structure without opening the website. "
    "Optional page inspection is a separate, user-triggered check and its results are not fed into the ML model."
)

if not MODEL_PATH.exists() or not META_PATH.exists():
    st.error("Trained model files are missing. Open the project terminal and run: `python src/train_model.py`")
    st.stop()

@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)

model = load_model()
metadata = json.loads(META_PATH.read_text(encoding="utf-8"))

with st.sidebar:
    st.header("Model information")
    st.write(f"**Selected model:** {metadata['best_model']}")
    st.write(f"**Dataset:** {metadata['dataset_name']} (UCI ID {metadata['uci_dataset_id']})")
    st.write(f"**Training records:** {metadata['train_records']:,}")
    st.write(f"**Testing records:** {metadata['test_records']:,}")
    st.write(f"**URL features:** {metadata['feature_count']}")
    st.divider()
    st.caption("Educational prototype. Never treat its output as a guarantee that a site is safe or malicious.")

st.subheader("1. Enter a website URL")
with st.form("url_analysis_form"):
    entered_url = st.text_input(
        "Website URL",
        placeholder="https://example.com/login",
        help="Paste a URL. If the scheme is omitted, https:// is added for analysis.",
    )
    submitted = st.form_submit_button("Analyze URL", type="primary", use_container_width=True)

if submitted:
    for key in ("last_url", "last_feature_frame", "last_prediction", "last_phishing_score", "page_inspection_result", "page_inspection_error"):
        st.session_state.pop(key, None)
    try:
        normalized = normalize_user_url(entered_url)
        feature_dict = extract_url_features(normalized)
        feature_frame = pd.DataFrame([feature_dict], columns=FEATURE_NAMES)
        prediction = int(model.predict(feature_frame)[0])
        phishing_score = float(model.predict_proba(feature_frame)[0][list(model.classes_).index(1)])
        st.session_state["last_url"] = normalized
        st.session_state["last_feature_frame"] = feature_frame
        st.session_state["last_prediction"] = prediction
        st.session_state["last_phishing_score"] = phishing_score
        st.session_state.pop("page_inspection_result", None)
    except Exception as exc:
        st.error(str(exc))

if "last_prediction" in st.session_state:
    prediction = st.session_state["last_prediction"]
    phishing_score = st.session_state["last_phishing_score"]
    analyzed_url = st.session_state["last_url"]
    st.subheader("2. Machine-learning result")
    left, right = st.columns([1.25, 1])
    if prediction == 1:
        left.error("Prediction: PHISHING-LIKE URL")
    else:
        left.success("Prediction: LEGITIMATE-LIKE URL")
    right.metric("Model-estimated phishing score", f"{phishing_score:.1%}")
    st.progress(max(0.0, min(1.0, phishing_score)))
    st.caption("This is a model score, not a calibrated guarantee or a definitive security verdict.")
    st.code(analyzed_url, language="text")

    with st.expander("View automatically extracted URL and domain features", expanded=True):
        feature_frame = st.session_state["last_feature_frame"]
        display = feature_frame.T.reset_index()
        display.columns = ["Feature", "Extracted value"]
        st.dataframe(display, hide_index=True, use_container_width=True)

    st.subheader("3. Optional webpage and domain inspection")
    st.warning(
        "This optional action sends a small HTTP GET request to the entered public website from your computer. "
        "The website can see your IP address. Do not inspect private/internal sites or URLs containing personal tokens. "
        "The inspector blocks local/private IP destinations, non-standard ports, and unsafe redirects."
    )
    if st.button("Inspect public webpage signals (optional)", use_container_width=True):
        with st.spinner("Checking DNS, HTTPS response and page HTML..."):
            try:
                st.session_state["page_inspection_result"] = inspect_public_page(analyzed_url)
            except Exception as exc:
                st.session_state["page_inspection_error"] = str(exc)
                st.session_state.pop("page_inspection_result", None)
    if "page_inspection_error" in st.session_state:
        st.error(st.session_state.pop("page_inspection_error"))
    if "page_inspection_result" in st.session_state:
        result = dict(st.session_state["page_inspection_result"])
        st.caption(result.pop("note", "Supplementary page observations."))
        title = result.get("page_title") or "(No title tag found)"
        st.write(f"**Page title:** {title}")
        signal_rows = [(key.replace("_", " ").title(), value) for key, value in result.items() if key not in {"page_title", "requested_url", "final_url"}]
        st.dataframe(pd.DataFrame(signal_rows, columns=["Page signal", "Observed value"]), hide_index=True, use_container_width=True)
        st.caption("Page observations are supplemental. They do not change or override the ML prediction above.")

with st.expander("How this project works"):
    st.markdown(
        """
        1. **URL input:** the user pastes a website URL.
        2. **Feature extraction:** Python derives URL length, host/domain structure, subdomains,
           character ratios, obfuscation indicators, query patterns, HTTPS usage and other lexical signals.
        3. **Classification:** the selected model predicts phishing-like or legitimate-like from the extracted features.
        4. **Optional page inspection:** a separate safe-mode check can inspect a small amount of public HTML.

        The optional page-inspection signals are shown for explanation only; the trained classifier is URL-feature based.
        The system does not execute JavaScript, submit forms, log in, or guarantee website safety.
        """
    )

st.divider()
st.caption(
    "Dataset: Prasad & Chandra (2024), PhiUSIIL Phishing URL (Website), UCI Machine Learning Repository, "
    "dataset ID 967. The model uses raw URL strings and project-defined lexical/domain features; it does not use "
    "the dataset's precomputed page-content fields at prediction time."
)
