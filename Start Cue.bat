@echo off
title Cue: Movies and Music Explorer
cd /d "%~dp0"
echo Starting Cue... your browser will open in a few seconds.
echo Keep this window open while you use Cue. Close it to stop Cue.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
echo.
echo Cue has stopped. If you see an error above, send Claude a screenshot.
pause
