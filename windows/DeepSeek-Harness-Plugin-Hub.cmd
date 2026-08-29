@echo off
rem DeepSeek Harness Desktop: built-in dsh plugin hub (Windows, Tkinter UI).
setlocal
set "APP=%~dp0..\bin\deepseek-harness-desktop"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "DeepSeek Harness Plugin Hub" pythonw "%APP%" --plugins
  exit /b 0
)
where py >nul 2>nul
if %errorlevel%==0 (
  start "DeepSeek Harness Plugin Hub" py -3 "%APP%" --plugins
  exit /b 0
)
echo Python 3 is required. Install it from https://www.python.org/downloads/
pause
exit /b 1
