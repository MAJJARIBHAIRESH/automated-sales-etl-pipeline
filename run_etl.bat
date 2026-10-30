@echo off
cd /d "C:\Users\Bhiresh\data-engineering-project"

call .venv\Scripts\activate.bat

python load_to_mysql.py

pause