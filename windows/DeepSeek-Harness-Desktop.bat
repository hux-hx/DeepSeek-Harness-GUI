@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: DeepSeek Harness Desktop Launcher
:: This script finds and launches the dsh web UI in a native window

:: Find dsh installation
set "DSH_FOUND="
for %%d in (dsh) do (
    for /f "tokens=*" %%p in ('where %%d 2^>nul') do (
        set "DSH_PATH=%%p"
        set "DSH_DIR=%%~dp"
        goto :found
    )
)
:found

if not defined DSH_PATH (
    echo Error: dsh not found. Install with: npm i -g @deepseek-ai/dsh
    pause
    exit /b 1
)

:: Set up app data directory
set "APP_DATA=%APPDATA%\DeepSeekHarnessDesktop"
if not exist "%APP_DATA%" mkdir "%APP_DATA%"

:: Launch dsh web
echo Starting DeepSeek Harness Desktop...
echo Using dsh: %DSH_PATH%

:: Run the desktop launcher
"%DSH_DIR%\..\..\lib\node_modules\@deepseek-ai\dsh\bin\dsh.js" web --no-open --port 0
