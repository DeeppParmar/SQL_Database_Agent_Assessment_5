@echo off
setlocal enabledelayedexpansion
title "SQL & Database Analytics Agent"

if "%1"=="install" goto do_install
if "%1"=="seed" goto do_seed
if "%1"=="test" goto do_test
if "%1"=="ui" goto do_ui
if "%1"=="all" goto do_all

:menu
cls
echo ========================================================
echo        SQL ^& Database Analytics Agent Launcher
echo ========================================================
echo.
echo  [1] Seed Database (Orders ^& Products tables)
echo  [2] Run Automated Tests (pytest - 15 test cases)
echo  [3] Launch Streamlit UI Dashboard
echo  [4] Run All (Seed -^> Run Tests -^> Launch UI)
echo  [5] Install Dependencies (requirements.txt)
echo  [0] Exit
echo.
echo ========================================================
set /p choice="Select an option [0-5]: "

if "%choice%"=="1" goto do_seed
if "%choice%"=="2" goto do_test
if "%choice%"=="3" goto do_ui
if "%choice%"=="4" goto do_all
if "%choice%"=="5" goto do_install
if "%choice%"=="0" exit /b 0

echo Invalid selection. Please try again.
timeout /t 2 >nul
goto menu

:do_install
echo.
echo [*] Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [!] Failed to install dependencies.
) else (
    echo [+] Dependencies installed successfully.
)
pause
goto menu

:do_seed
echo.
echo [*] Seeding sample database tables...
python seed_db.py
if errorlevel 1 (
    echo [!] Database seeding failed.
) else (
    echo [+] Database seeded successfully.
)
if "%1"=="seed" exit /b 0
pause
goto menu

:do_test
echo.
echo [*] Running automated pytest suite...
python -m pytest -v
if errorlevel 1 (
    echo [!] Tests encountered errors.
) else (
    echo [+] All tests passed successfully!
)
if "%1"=="test" exit /b 0
pause
goto menu

:do_ui
echo.
echo [*] Launching Streamlit Analytics Dashboard...
python -m streamlit run app.py
if "%1"=="ui" exit /b 0
goto menu

:do_all
echo.
echo [Step 1/3] Seeding sample database...
python seed_db.py
echo.
echo [Step 2/3] Running automated tests...
python -m pytest -v
if errorlevel 1 (
    echo [!] Tests failed. Aborting dashboard launch.
    pause
    goto menu
)
echo.
echo [Step 3/3] Launching Streamlit UI Dashboard...
python -m streamlit run app.py
exit /b 0
