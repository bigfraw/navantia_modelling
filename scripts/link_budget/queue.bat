@echo off
rem The 10 km MMF evaluation queue on bigfraw (GPU). Launch it through WMI.
rem Each step appends to queue.log; "EXIT n" closes each step.
cd /d D:\repos\navantia_modelling\scripts\link_budget
set PY=C:\Users\alexf\olb-gpu-venv\Scripts\python.exe -u
set LOG=queue.log

call :step uncorrected.py --case b36_2in_circle b18_1in_ellipse
call :step uncorrected.py --case b9_1in_circle b18_1in_circle --cn2 1e-15
call :step uncorrected.py --case b9_1in_circle --cn2 5e-15
call :step tt_pass.py --case b36_2in_circle
call :step tt_pass.py --case b18_1in_ellipse
call :step uncorrected.py --case b18_1in_circle --cn2 5e-15 1e-14
call :step tt_pass.py --case b18_1in_circle
call :step uncorrected.py --case b9_1in_ellipse
call :step uncorrected.py --case b9_1in_circle --cn2 1e-14
call :step tt_pass.py --case b9_1in_circle b9_1in_ellipse
echo QUEUE DONE >> %LOG%
goto :eof

:step
echo ==== %date% %time% %* >> %LOG%
%PY% %* >> %LOG% 2>&1
echo EXIT %ERRORLEVEL% >> %LOG%
goto :eof
