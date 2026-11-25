"""Generate a populated DOCX report from the URL-model training artifacts."""
from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent
ART = ROOT / "artifacts"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
OUT = REPORTS / "Project_Report_Final.docx"


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, color=None, size=8.5):
    cell.text = str(text)
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_after = Pt(2)
        for run in paragraph.runs:
            run.bold = bold
            run.font.name = "Aptos"
            run.font.size = Pt(size)
            if color:
                run.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Shading Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], header, True, (255, 255, 255), 8.5)
        shade(table.rows[0].cells[i], "1F4E78")
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            set_cell_text(cells[i], value, size=8)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        p.add_run(item)


def add_numbered(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        p.paragraph_format.space_after = Pt(2)
        p.add_run(item)


def main():
    required = [
        ART / "model_metadata.json", ART / "model_comparison.csv",
        ART / "confusion_matrix.csv", ART / "classification_report.txt",
        ART / "feature_importance.csv", ART / "best_url_model.joblib",
    ]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        raise SystemExit("Run `python src/train_model.py` first. Missing artifacts: " + ", ".join(missing))

    meta = json.loads((ART / "model_metadata.json").read_text(encoding="utf-8"))
    comparison = pd.read_csv(ART / "model_comparison.csv")
    cm = pd.read_csv(ART / "confusion_matrix.csv", index_col=0)
    importance = pd.read_csv(ART / "feature_importance.csv").head(10)
    report_text = (ART / "classification_report.txt").read_text(encoding="utf-8")
    errors = pd.read_csv(ART / "error_analysis.csv") if (ART / "error_analysis.csv").exists() else pd.DataFrame()

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.65)
    sec.bottom_margin = Inches(0.65)
    sec.left_margin = Inches(0.75)
    sec.right_margin = Inches(0.75)
    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9.5)
    styles["Normal"].paragraph_format.space_after = Pt(4)
    for style_name in ("Title", "Heading 1", "Heading 2"):
        styles[style_name].font.name = "Aptos Display"
        styles[style_name].font.color.rgb = RGBColor(31, 78, 121)
    styles["Heading 1"].font.size = Pt(15)
    styles["Heading 2"].font.size = Pt(11)

    # Cover
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(78)
    r = p.add_run("PHISHING WEBSITE DETECTION\n")
    r.bold = True; r.font.size = Pt(25); r.font.color.rgb = RGBColor(31, 78, 121)
    r = p.add_run("URL-Enabled Machine Learning Project")
    r.bold = True; r.font.size = Pt(16)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    p.add_run("B.Tech - Artificial Intelligence and Data Science\n").bold = True
    p.add_run("Classification | URL Feature Extraction | UCI PhiUSIIL Dataset")
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(55)
    for line in [
        "Student Name: __________________________________________",
        "Roll Number: ____________________________________________",
        "Department / College: ____________________________________",
        "Faculty Guide: ___________________________________________",
        "Academic Year: __________________________________________",
    ]:
        doc.add_paragraph(line)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(70)
    p.add_run("Project report generated from the actual local training run.").italic = True
    doc.add_page_break()

    doc.add_heading("Abstract", 1)
    doc.add_paragraph(
        f"This project develops a URL-first supervised machine-learning system to classify raw website URLs as "
        f"phishing-like or legitimate-like. It uses {meta['records_loaded']:,} usable URL records from the UCI "
        f"PhiUSIIL Phishing URL (Website) dataset (ID 967), after cleaning and duplicate/conflict handling. "
        f"A deterministic Python feature extractor converts each raw URL into {meta['feature_count']} numerical "
        f"URL/domain characteristics. Logistic Regression, Decision Tree, Linear SVM and Gaussian Naive Bayes "
        f"are compared. The selected model is {meta['best_model']}, chosen by 5-fold stratified group cross-validation "
        f"using F1-score. A Streamlit application accepts a pasted URL and extracts the same features before prediction. "
        f"An optional, separate public-page inspection presents supporting HTML observations; those observations are "
        f"not part of the classifier input. This is an educational prototype, not a production security guarantee."
    )

    doc.add_heading("1. Problem Definition and Objectives", 1)
    doc.add_paragraph(
        "Phishing websites use deceptive URLs and website appearances to trick people into disclosing credentials, "
        "payment details or other sensitive information. Manual inspection is inconsistent. This project uses "
        "machine-learning classification to identify URL patterns associated with phishing and provides an "
        "interactive prototype for classroom demonstration."
    )
    add_bullets(doc, [
        "Use a documented public dataset that includes raw URL strings and phishing/legitimate labels.",
        "Clean URL records and transform each URL into a consistent numeric feature vector.",
        "Compare four classification algorithms from the course project's suggested family.",
        "Use host-group-aware validation and a separate test partition to reduce hostname leakage.",
        "Evaluate accuracy, precision, recall, F1-score, ROC-AUC and confusion-matrix errors.",
        "Build a Streamlit interface that accepts a website URL rather than requiring manual feature entry.",
        "Document privacy, safety, limitations and responsible-use considerations.",
    ])

    doc.add_heading("2. Dataset Description", 1)
    add_table(doc, ["Item", "Description"], [
        ("Dataset", meta["dataset_name"]),
        ("Source", "UCI Machine Learning Repository, dataset ID 967"),
        ("Published size", "235,795 records; 54 dataset features (UCI published metadata)"),
        ("Fields used in this experiment", "Raw URL text and target label only"),
        ("Records used after URL validation", f"{meta.get('records_after_url_validation', meta['records_loaded']):,}"),
        ("Invalid URLs skipped", f"{meta.get('invalid_urls_skipped', 0):,}"),
        ("Duplicate records removed", f"{meta.get('duplicates_removed', 0):,}"),
        ("Conflicting URL rows removed", f"{meta.get('conflicting_url_rows_removed', 0):,}"),
        ("Label mapping", "UCI: 0 = phishing, 1 = legitimate; project: 1 = phishing, 0 = legitimate"),
        ("Class counts", f"Legitimate: {meta['class_counts']['legitimate_0']:,}; Phishing: {meta['class_counts']['phishing_1']:,}"),
        ("License", "Creative Commons Attribution 4.0 International (CC BY 4.0)"),
    ])
    doc.add_paragraph(
        "The source dataset contains additional engineered URL and webpage fields. This implementation deliberately "
        "uses the raw URL and label only, then computes its own URL feature vector. This avoids training the classifier "
        "on webpage fields that the URL-only prediction path does not compute."
    )

    doc.add_heading("3. Methodology", 1)
    doc.add_paragraph(
        "Dataset acquisition -> URL cleaning and duplicate audit -> deterministic URL feature extraction -> "
        "hostname-group train/test split -> 5-fold stratified group cross-validation -> model comparison -> "
        "held-out testing -> error/feature analysis -> Streamlit prediction prototype."
    )
    add_table(doc, ["Step", "Implementation"], [
        ("Data acquisition", "Fetch UCI PhiUSIIL dataset ID 967 using ucimlrepo; cache only URL and label locally."),
        ("Preprocessing", "Remove blank URLs, invalid labels, duplicate normalized URLs and conflicting duplicate URL groups."),
        ("Feature extraction", f"Apply one shared extractor to raw URL strings to produce {meta['feature_count']} numeric URL/domain features."),
        ("Data split", f"Approximately 80:20 host-group-aware split; train={meta['train_records']:,}, test={meta['test_records']:,}."),
        ("Validation", "5-fold StratifiedGroupKFold; all URLs from a hostname stay in one fold."),
        ("Model selection", meta["selection_method"]),
        ("Evaluation", "Accuracy, phishing precision/recall/F1, ROC-AUC, confusion matrix and error analysis."),
        ("Interpretation", "Permutation importance on a bounded sample from the held-out test partition."),
    ])

    doc.add_heading("4. URL Feature Extraction", 1)
    doc.add_paragraph(
        "The user enters a raw URL. The same local Python function is used while preparing training data and while "
        "analyzing a new URL. No network request is needed for the ML feature extraction step. The features represent "
        "URL length and structure, host/domain structure, subdomain count, top-level-domain length, HTTPS scheme, "
        "non-standard ports, IP-based hosts, punycode, percent-encoding, character ratios, query patterns, URL entropy, "
        "known URL shorteners and suspicious keyword counts."
    )
    doc.add_paragraph(
        "The optional page-inspection button separately checks a small amount of public HTML after user action. "
        "It can display title, form, password/hidden-field, iframe, link and resource observations. These are supporting "
        "observations only and are not fed into the machine-learning classifier."
    )

    doc.add_heading("5. Algorithms Implemented", 1)
    add_table(doc, ["Algorithm", "Purpose"], [
        ("Logistic Regression", "Linear classifier that estimates class probabilities from the extracted numeric features."),
        ("Decision Tree", "Rule-based classifier that can learn nonlinear feature interactions."),
        ("Linear Support Vector Machine", "Finds a separating hyperplane between phishing and legitimate URL feature vectors."),
        ("Gaussian Naive Bayes", "Probabilistic baseline based on conditional-independence assumptions for numeric features."),
    ])

    doc.add_page_break()
    doc.add_heading("6. Experimental Results", 1)
    rows = []
    for _, row in comparison.iterrows():
        rows.append((
            row["model"], f"{row['cv_f1_mean']:.4f} ± {row['cv_f1_std']:.4f}",
            f"{row['test_accuracy']:.4f}", f"{row['test_precision_phishing']:.4f}",
            f"{row['test_recall_phishing']:.4f}", f"{row['test_f1_phishing']:.4f}",
            f"{row['test_roc_auc']:.4f}",
        ))
    add_table(doc, ["Model", "CV F1 ± SD", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"], rows)
    doc.add_paragraph(
        f"Selected model: {meta['best_model']}. It was selected using the highest mean F1-score from "
        "5-fold stratified group cross-validation on the training partition. Metrics are specific to this dataset "
        "and split; they are not a promise of performance on live internet traffic."
    )
    doc.add_heading("Confusion Matrix", 2)
    cm_rows = [(idx, int(cm.loc[idx].iloc[0]), int(cm.loc[idx].iloc[1])) for idx in cm.index]
    add_table(doc, ["Actual class", "Predicted legitimate", "Predicted phishing"], cm_rows)
    if (FIGURES / "confusion_matrix.png").exists():
        doc.add_picture(str(FIGURES / "confusion_matrix.png"), width=Inches(4.9))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_heading("Classification Report", 2)
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    r = p.add_run(report_text)
    r.font.name = "Consolas"; r.font.size = Pt(7.5)
    if not errors.empty:
        false_negatives = int((errors["error_type"] == "False Negative (phishing missed)").sum())
        false_positives = int((errors["error_type"] == "False Positive (legitimate flagged)").sum())
        doc.add_paragraph(
            f"The held-out test partition contained {false_negatives} false negatives (phishing URLs predicted as "
            f"legitimate) and {false_positives} false positives (legitimate URLs predicted as phishing)."
        )

    doc.add_page_break()
    doc.add_heading("7. Model Interpretation", 1)
    doc.add_paragraph(
        "Permutation importance estimates how much the selected model's F1-score changes when one extracted feature "
        "is randomly shuffled on a held-out sample. It is a model-agnostic diagnostic, not proof of causation."
    )
    add_table(doc, ["Feature", "Mean importance", "Standard deviation"], [
        (r["feature"], f"{r['importance_mean']:.6f}", f"{r['importance_std']:.6f}")
        for _, r in importance.iterrows()
    ])
    if (FIGURES / "feature_importance.png").exists():
        doc.add_picture(str(FIGURES / "feature_importance.png"), width=Inches(5.4))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_page_break()
    doc.add_heading("8. Working Prototype", 1)
    doc.add_paragraph(
        "The Streamlit application accepts a user-entered website URL. It automatically normalizes the input, "
        "extracts the 32 URL/domain features locally, loads the selected model and displays a phishing-like or "
        "legitimate-like prediction with a model-estimated score. The user can inspect the extracted feature table."
    )
    doc.add_paragraph("Run command: streamlit run app.py")
    doc.add_heading("Optional webpage inspection", 2)
    doc.add_paragraph(
        "After explicit user action, the application can make a bounded HTTP GET to a public website and parse a "
        "limited amount of HTML. It blocks local/private/reserved destinations and unsafe redirects, permits only "
        "HTTP/HTTPS on standard ports, uses short timeouts and a response-size limit, and does not execute JavaScript, "
        "submit forms, use cookies or log in. The collected page observations are displayed separately and do not "
        "alter the classifier's output. The destination can observe the user's IP address."
    )

    doc.add_page_break()
    doc.add_heading("9. Limitations and Responsible Use", 1)
    add_bullets(doc, [
        "The classifier uses URL-string features. It does not use live webpage HTML features in its ML prediction.",
        "The optional page inspection is a separate evidence panel and may fail on blocked, unavailable or non-HTML sites.",
        "URL lexical features may miss phishing pages hosted on compromised legitimate domains or URLs with little visible obfuscation.",
        "Dataset performance does not guarantee real-world performance; new campaigns and temporal shifts require fresh validation.",
        "A high model score does not prove maliciousness and a low score does not prove safety.",
        "Use only for educational and defensive awareness. Do not make security, financial or access decisions solely from this prototype.",
    ])

    doc.add_heading("10. Reproducibility", 1)
    add_numbered(doc, [
        "Create and activate a Python virtual environment.",
        "Install dependencies with: python -m pip install -r requirements.txt",
        "Train and evaluate the classifiers: python src/train_model.py",
        "Generate the populated report: python generate_report.py",
        "Launch the application: streamlit run app.py",
    ])
    doc.add_paragraph(
        "The downloaded URL/label cache is stored in data/. Model metadata, selected model, comparison metrics, "
        "confusion matrix, classification report, error analysis and feature importance are stored in artifacts/. "
        "Charts are stored in reports/figures/. These generated files are reproducible and excluded from Git by default."
    )

    doc.add_heading("References", 1)
    doc.add_paragraph(
        "1. Prasad, A. & Chandra, S. (2024). PhiUSIIL Phishing URL (Website). UCI Machine Learning Repository. "
        "https://doi.org/10.1016/j.cose.2023.103545."
    )
    doc.add_paragraph("2. UCI Machine Learning Repository. PhiUSIIL Phishing URL (Website), dataset ID 967.")
    doc.add_paragraph("3. Scikit-learn documentation. https://scikit-learn.org/stable/")
    doc.add_paragraph("4. Streamlit documentation. https://docs.streamlit.io/")
    doc.add_paragraph("5. Beautiful Soup documentation. https://www.crummy.com/software/BeautifulSoup/bs4/doc/")

    for section in doc.sections:
        hp = section.header.paragraphs[0]
        hp.text = "B.Tech AI & DS | Machine Learning Project"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fp = section.footer.paragraphs[0]
        fp.text = "Phishing Website Detection | URL-Enabled Project Report"
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    REPORTS.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Report generated: {OUT}")


if __name__ == "__main__":
    main()
