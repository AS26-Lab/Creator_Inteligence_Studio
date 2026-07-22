@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Error: no se encontro el interprete del proyecto en "%PYTHON%".
  echo Cree .venv antes de ejecutar la aplicacion.
  exit /b 1
)

"%PYTHON%" -m creator_intelligence_studio %*
exit /b %ERRORLEVEL%

