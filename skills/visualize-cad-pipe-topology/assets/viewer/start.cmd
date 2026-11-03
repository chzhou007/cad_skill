@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0launch_review.py" goto incomplete
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 goto use_py
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 goto use_python
echo STARTUP FAILED: Python 3.10 or newer was not found.
echo Install Python 3.10+ from python.org, then reopen this launcher.
echo Python 3.10 or newer was not found.> "%~dp0startup-error.txt"
goto failed
:use_py
py -3 -X utf8 -u "%~dp0launch_review.py" %*
goto result
:use_python
python -X utf8 -u "%~dp0launch_review.py" %*
:result
set "launch_exit=%errorlevel%"
if not "%launch_exit%"=="0" goto failed
exit /b 0
:incomplete
echo STARTUP FAILED: launcher files are missing. Extract the complete ZIP first.
:failed
echo.
echo Keep this message for diagnosis. Check startup-logs if present.
pause
exit /b 1
