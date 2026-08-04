@echo off
setlocal
set "CIS_GUI_TEST_MODE=1"
set "QT_QPA_PLATFORM=offscreen"
set "CIS_GUI_AUTO_EXIT_MS=1000"
set "CIS_RUN_GUI_TESTS=1"
pushd "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
    echo Error: no se encontro .venv\Scripts\python.exe
    exit /b 1
)
".venv\Scripts\python.exe" -m creator_intelligence_studio --gui
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
