@echo off
setlocal enabledelayedexpansion
title "SQL & Database Analytics Agent - All-in-One"

cd /d "%~dp0"

:: Auto-setup .env if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Initializing .env from .env.example...
        copy ".env.example" ".env" >nul
    )
)

:: Direct CLI argument routing
if /i "%1"=="all" goto do_all
if /i "%1"=="ui" goto do_ui
if /i "%1"=="test" goto do_test
if /i "%1"=="tc1" goto do_tc1
if /i "%1"=="tc2" goto do_tc2
if /i "%1"=="seed" goto do_seed
if /i "%1"=="install" goto do_install

:menu
cls
echo =====================================================================
echo           SQL ^& Database Analytics Agent - All-in-One Runner
echo =====================================================================
echo.
echo   [1] ALL-IN-ONE (Seed DB -^> Run Tests -^> Launch Web Dashboard)  *DEFAULT*
echo   [2] Launch Streamlit Analytics Dashboard Only
echo   [3] Run Automated Pytest Suite (15 Unit ^& Security Tests)
echo   [4] Verify Test Case 1: SQL Self-Correction Column Recovery Loop
echo   [5] Verify Test Case 2: AST Safety Filter ^& SQL Injection Block
echo   [6] Seed Database (Orders ^& Products tables)
echo   [7] Install / Check Dependencies (requirements.txt)
echo   [0] Exit
echo.
echo =====================================================================
set /p choice="Enter choice [1-7 or 0, Default=1]: "

if "%choice%"=="" goto do_all
if "%choice%"=="1" goto do_all
if "%choice%"=="2" goto do_ui
if "%choice%"=="3" goto do_test
if "%choice%"=="4" goto do_tc1
if "%choice%"=="5" goto do_tc2
if "%choice%"=="6" goto do_seed
if "%choice%"=="7" goto do_install
if "%choice%"=="0" exit /b 0

echo Invalid choice. Try again.
timeout /t 2 >nul
goto menu

:do_all
echo.
echo =====================================================================
echo  [Step 1/3] Seeding Database...
echo =====================================================================
python seed_db.py
if errorlevel 1 (
    echo [!] Seeding failed.
    if "%1"=="" pause
    goto menu
)
echo.
echo =====================================================================
echo  [Step 2/3] Running Automated Pytest Suite...
echo =====================================================================
python -m pytest -v
if errorlevel 1 (
    echo [!] Test suite encountered errors.
    if "%1"=="" pause
    goto menu
)
echo.
echo =====================================================================
echo  [Step 3/3] Launching Streamlit Web UI Dashboard...
echo =====================================================================
python -m streamlit run app.py
if errorlevel 1 (
    echo [!] Failed to launch dashboard.
    if "%1"=="" pause
)
exit /b 0

:do_ui
echo.
echo [*] Launching Streamlit Analytics Dashboard...
python -m streamlit run app.py
if not "%1"=="" exit /b 0
pause
goto menu

:do_test
echo.
echo [*] Running automated pytest suite...
python -m pytest -v
echo.
if not "%1"=="" exit /b 0
pause
goto menu

:do_tc1
echo.
echo [*] Executing Test Case 1 (Self-Correction Reflection Recovery)...
python verify_cases.py tc1
echo.
if not "%1"=="" exit /b 0
pause
goto menu

:do_tc2
echo.
echo [*] Executing Test Case 2 (AST ^& NeMo SQL Injection Block)...
python verify_cases.py tc2
echo.
if not "%1"=="" exit /b 0
pause
goto menu

:do_seed
echo.
echo [*] Seeding sample database tables...
python seed_db.py
echo.
if not "%1"=="" exit /b 0
pause
goto menu

:do_install
echo.
echo [*] Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
echo.
if not "%1"=="" exit /b 0
pause
goto menu
