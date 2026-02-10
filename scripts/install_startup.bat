@echo off
REM TDK2-Traceability Auto-Startup Installation Script
REM This script configures Windows Task Scheduler to start TDK2-Traceability on user login

echo ========================================
echo TDK2-Traceability Auto-Startup Installation
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

REM Get the directory where this script is located and go up one level
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"
cd ..
set "APP_DIR=%CD%"
popd
set "EXE_PATH=%APP_DIR%\TDK2-Traceability.exe"

REM Verify executable exists
if not exist "%EXE_PATH%" (
    echo ERROR: TDK2-Traceability.exe not found at: %EXE_PATH%
    echo.
    echo Expected location: %EXE_PATH%
    echo Script location: %SCRIPT_DIR%
    echo.
    echo Please ensure this script is in the scripts\ folder of the TDK2-Traceability installation
    echo and that TDK2-Traceability.exe is in the parent directory.
    pause
    exit /b 1
)

echo Script directory: %SCRIPT_DIR%
echo Application directory: %APP_DIR%
echo Executable path: %EXE_PATH%
echo.

REM Create Task Scheduler entry
echo Creating Task Scheduler entry...
schtasks /Create /TN "TDK2 Traceability" /TR "\"%EXE_PATH%\"" /SC ONLOGON /RL HIGHEST /F /DELAY 0000:30 >nul 2>&1

if %errorLevel% equ 0 (
    echo.
    echo SUCCESS: Auto-startup configured successfully!
    echo.
    echo The TDK2-Traceability application will start automatically 30 seconds after user login.
    echo.
    echo To verify the task was created:
    echo   schtasks /Query /TN "TDK2 Traceability"
    echo.
    echo To remove auto-startup, run: uninstall_startup.bat
) else (
    echo.
    echo ERROR: Failed to create Task Scheduler entry
    echo Error code: %errorLevel%
    echo.
    echo You can manually create the task using Task Scheduler (taskschd.msc)
)

echo.
pause
