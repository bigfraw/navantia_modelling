@echo off
rem The turbulent divergence-jitter sweep on bigfraw (GPU). Each step appends to divergence_jitter.log.
cd /d D:\repos\navantia_modelling
set PYTHONPATH=D:\repos\optical_link_budget
set PY=C:\Users\alexf\olb-gpu-venv\Scripts\python.exe -u -W ignore scripts\divergence_jitter_sweep.py turb --trials 1000
set LOG=scripts\divergence_jitter_data\divergence_jitter.log

for %%d in (54 75 100 150 200 300) do call :step --div %%d
echo QUEUE DONE >> %LOG%
goto :eof

:step
echo ==== %date% %time% %* >> %LOG%
%PY% %* >> %LOG% 2>&1
echo EXIT %ERRORLEVEL% >> %LOG%
goto :eof
