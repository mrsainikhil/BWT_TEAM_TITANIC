@echo off
setlocal
cd /d "%~dp0"
set PYEXE=%LocalAppData%\Programs\Python\Python313\python.exe
if not exist "%PYEXE%" set PYEXE=python
"%PYEXE%" -m pip install -r requirements.txt
start "" "%PYEXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
start "" "http://localhost:8000/"
endlocal
