# Generated reports and figures

This folder receives output after running:

```powershell
python src/train_model.py
python generate_report.py
```

The training script writes evaluation figures to `reports/figures/`. The report generator writes `Project_Report_Final.docx` here using metrics from the local training run. Generated outputs are ignored by Git by default to keep the source repository small; upload the final DOCX separately only when your instructor requests it.
