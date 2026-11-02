@echo off
rem The cropped-grid check of the 10 km MMF evaluation on bigfraw (GPU). Each step appends to queue_crop.log.
cd /d D:\repos\navantia_modelling\scripts\link_budget
set PY=C:\Users\alexf\olb-gpu-venv\Scripts\python.exe -u -W ignore
set LOG=queue_crop.log

call :step uncorrected.py --case b18_1in_circle --cn2 5e-15 1e-14 --crop 2
call :step uncorrected.py --case b9_1in_circle --cn2 5e-15 1e-14 --crop 2
call :step uncorrected.py --case b9_1in_circle --cn2 1e-14 --crop 3
echo QUEUE DONE >> %LOG%
goto :eof

:step
echo ==== %date% %time% %* >> %LOG%
%PY% %* >> %LOG% 2>&1
echo EXIT %ERRORLEVEL% >> %LOG%
goto :eof
