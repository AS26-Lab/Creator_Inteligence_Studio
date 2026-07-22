@echo off
setlocal
pushd "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
    echo Error: no se encontro .venv\Scripts\python.exe
    exit /b 1
)
".venv\Scripts\python.exe" -m creator_intelligence_studio --gui
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
