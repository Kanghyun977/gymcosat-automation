@echo off
chcp 65001 >nul
cd /d "C:\Users\KANG\OneDrive\바탕 화면\claud-test\gymcosat-automation"
set PYTHONIOENCODING=utf-8
"C:\Users\KANG\AppData\Local\Programs\Python\Python313\python.exe" scripts\daily_publish.py >> logs\scheduler.log 2>&1
