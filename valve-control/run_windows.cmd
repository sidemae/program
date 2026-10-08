@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" valve_control.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo 실행에 실패했습니다. 위의 오류를 확인하세요.
pause
exit /b 1
