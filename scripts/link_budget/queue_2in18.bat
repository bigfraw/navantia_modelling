@echo off
rem The 18.2 mm (8 x 2.27 mm) launch on a clear 2 in aperture, 10 km. Launch it
rem through WMI. Each step appends to queue_2in18.log; "EXIT n" closes each step.
cd /d D:\repos\navantia_modelling\scripts\link_budget
set PY=C:\Users\alexf\olb-gpu-venv\Scripts\python.exe -u
set LOG=queue_2in18.log

call :step uncorrected.py --case b18_2in_circle
call :step tt_pass.py --case b18_2in_circle
echo QUEUE DONE >> %LOG%
goto :eof

:step
echo ==== %date% %time% %* >> %LOG%
%PY% %* >> %LOG% 2>&1
echo EXIT %ERRORLEVEL% >> %LOG%
goto :eof
