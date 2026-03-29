@echo off
:: Move to the directory where this batch file lives
cd /d "%~dp0"

:: Activate the virtual environment located two levels back
call ..\..\venv\Scripts\activate

:: Run the application
python main.py

:: Keep the window open so you can see the results
pause