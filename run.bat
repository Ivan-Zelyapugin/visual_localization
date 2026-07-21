
@echo off
set PYTHONPATH=src
.venv\Scripts\python.exe scripts/main.py --yolo-model best_2.pt --yolo-device cuda --yolo-conf 0.5
pause
