# Contributing

Thanks for your interest in improving this educational project.

## Setup

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1   |   macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Guidelines

- Keep the training-time and inference-time URL feature schemas identical (`src/url_features.py` is the single source of truth).
- Do not silently change feature order or the label mapping (`1 = phishing`, `0 = legitimate`).
- Keep the optional webpage inspection separate from the classifier unless the model is explicitly retrained with matching features.
- Add or update tests in `tests/` when URL parsing, feature extraction, data cleaning or inspector safeguards change.
- Do not commit `.env` files, credentials, local datasets, model binaries or generated outputs.
- Never paste metrics you did not produce: results in the README must come from `python scripts/results_to_markdown.py`.
- Document dataset changes, limitations and any change to the evaluation method.

## Pull requests

Describe what changed and why, how you tested it, and any impact on reproducibility or model results. Screenshots help for UI changes.
