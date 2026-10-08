@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PYTHONUTF8=1"
set "VALVE_PUSHED="
pushd "%~dp0"
if errorlevel 1 goto folder_error
set "VALVE_PUSHED=1"
if not exist "valve_control.py" goto files_error
if not exist "requirements.txt" goto files_error
if exist ".venv\Scripts\python.exe" goto check_venv
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 goto create_with_py
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 goto create_with_python
echo Python 3.11 or newer was not found.
echo Install Python from https://www.python.org/downloads/windows/
echo Enable the Python launcher or Add Python to PATH, then try again.
goto failed
:create_with_py
py -3 -m venv .venv
if errorlevel 1 goto failed
goto check_venv
:create_with_python
python -m venv .venv
if errorlevel 1 goto failed
:check_venv
".venv\Scripts\python.exe" -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto venv_error
".venv\Scripts\python.exe" -c "from PIL import Image, ImageTk; import PIL; assert PIL.__version__ == '12.3.0'" >nul 2>&1
if not errorlevel 1 goto run_app
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto failed
:run_app
".venv\Scripts\python.exe" valve_control.py %*
if errorlevel 1 goto failed
popd
exit /b 0
:folder_error
echo Cannot open the program folder.
goto failed
:files_error
echo Program files are missing. Extract the entire ZIP before running.
goto failed
:venv_error
echo The local virtual environment is invalid or lacks Tkinter.
echo Rename the .venv folder, then run this launcher again.
:failed
echo Launch failed. Review the error above.
pause
if defined VALVE_PUSHED popd
exit /b 1
