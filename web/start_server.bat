@echo off
echo Starting web server on port 8000...
echo.
echo Open your browser and navigate to: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.
cd /d %~dp0
python -m http.server 8000
pause





