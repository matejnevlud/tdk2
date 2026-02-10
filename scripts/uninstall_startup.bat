@echo off
REM TDK2-Traceability Auto-Startup Removal Script
REM This script removes the Windows Task Scheduler entry for TDK2-Traceability

echo ========================================
echo TDK2-Traceability Auto-Startup Removal
echo ========================================
echo.

REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check if task exists
schtasks /Query /TN "TDK2 Traceability" >nul 2>&1
if %errorLevel% neq 0 (
    echo Task "TDK2 Traceability" not found.
    echo Auto-startup may not be configured, or task was already removed.
    pause
    exit /b 0
)

echo Removing Task Scheduler entry...
schtasks /Delete /TN "TDK2 Traceability" /F >nul 2>&1

if %errorLevel% equ 0 (
    echo.
    echo SUCCESS: Auto-startup removed successfully!
    echo.
    echo TDK2-Traceability will no longer start automatically on login.
) else (
    echo.
    echo ERROR: Failed to remove Task Scheduler entry
    echo Error code: %errorLevel%
)

echo.
pause
