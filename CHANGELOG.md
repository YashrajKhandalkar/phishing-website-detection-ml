# Changelog

All notable changes to this project are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.1.0]

### Added
- `pytest` test suite for URL features, dataset cleaning/label mapping and inspector destination guards.
- GitHub Actions CI (Python 3.11-3.13), issue/PR templates and `SECURITY.md`.
- `scripts/results_to_markdown.py` to turn real training output into a README results table.
- `requirements-dev.txt` and `pyproject.toml` (test configuration).

### Changed
- README rewritten for GitHub (cross-platform setup, methodology, results workflow, limitations).
- Contributing guide updated; the upload how-to moved out of the repository.

## [1.0.0] - Initial URL-enabled project package

- Direct website URL input in the Streamlit application.
- Shared 32-feature URL/domain extractor for training and inference.
- UCI PhiUSIIL loader and cleaning workflow.
- Logistic Regression, Decision Tree, Linear SVM and Gaussian Naive Bayes comparison.
- Host-group-aware validation, test metrics, confusion matrix and permutation feature importance.
- Optional, separate public-page inspection with destination and request safeguards.
- DOCX report generation, Jupyter notebook, feature dictionary and viva questions.
