@echo off
set PYTHONPATH=e:\Data\Flora

start "Events" cmd /k python events/main.py
start "Interaction" cmd /k python interaction/main.py
start "Tasks" cmd /k python tasks/main.py
start "Trigger" cmd /k python trigger/main.py

echo 所有服务已启动（每个服务一个窗口）
pause