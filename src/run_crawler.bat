@echo off
:: Move to the directory where this batch file lives
cd /d "%~dp0"

:: Activate the virtual environment (one level up from src)
call ..\venv\Scripts\activate

:: Run the crawler
python jobs_crawler.py

:: Keep the window open so you can see the crawl logs
pause