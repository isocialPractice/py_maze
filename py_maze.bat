@echo off
REM py_maze launcher script for Windows
setlocal
REM run the package from this folder, so a checkout needs no install
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m py_maze %*
endlocal
