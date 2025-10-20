@echo off
setlocal enabledelayedexpansion

REM Check if uv is installed
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing uv package manager...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo Failed to install uv
        exit /b 1
    )
    REM Add uv to PATH for current session
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo Synchronizing Python environment with uv.lock
uv sync %*
if %errorlevel% neq 0 (
    echo Failed to sync environment
    exit /b 1
)

exit /b 0
