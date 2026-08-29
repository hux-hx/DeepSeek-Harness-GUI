@echo off
rem DeepSeek Harness Desktop (Windows): double-click launcher.
rem Boots the dsh web sidecar and opens it in a WebView2 window.
setlocal
set "APP=%~dp0..\bin\deepseek-harness-desktop"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "DeepSeek Harness" pythonw "%APP%" %*
  exit /b 0
)
where py >nul 2>nul
if %errorlevel%==0 (
  start "DeepSeek Harness" py -3 "%APP%" %*
  exit /b 0
)
echo Python 3 is required. Install it from https://www.python.org/downloads/
echo (enable "Add python.exe to PATH" and the tcl/tk component), then retry.
pause
exit /b 1
