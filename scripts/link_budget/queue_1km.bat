@echo off
rem The 1 km MMF evaluation queue on bigfraw (GPU). Launch it through WMI.
rem Each step appends to queue_1km.log; "EXIT n" closes each step.
cd /d D:\repos\navantia_modelling\scripts\link_budget
set PY=C:\Users\alexf\olb-gpu-venv\Scripts\python.exe -u
set LOG=queue_1km.log

call :step uncorrected.py --length-km 1 --case b18_1in_circle b18_1in_ellipse
call :step uncorrected.py --length-km 1 --case b36_2in_circle b9_1in_circle b9_1in_ellipse
call :step tt_pass.py --length-km 1 --trials 1000
echo QUEUE DONE >> %LOG%
goto :eof

:step
echo ==== %date% %time% %* >> %LOG%
%PY% %* >> %LOG% 2>&1
echo EXIT %ERRORLEVEL% >> %LOG%
goto :eof
