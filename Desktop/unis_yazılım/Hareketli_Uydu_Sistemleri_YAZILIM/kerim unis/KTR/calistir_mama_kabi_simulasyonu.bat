@echo off
set "SCRIPT_DIR=%~dp0"
set "SCRIPT=%SCRIPT_DIR%mama_kabi_stabilizasyon_python_arayuz.py"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PY%" (
  "%BUNDLED_PY%" "%SCRIPT%"
) else (
  python "%SCRIPT%"
)
