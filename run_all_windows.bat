@echo off
setlocal
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe src\train_model.py
.venv\Scripts\python.exe generate_report.py
.venv\Scripts\python.exe -m streamlit run app.py
endlocal
