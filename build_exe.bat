@echo off
setlocal

cd /d "%~dp0"
if errorlevel 1 (
    echo ERROR: Could not open the project directory.
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON=py -3"
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo ERROR: Python 3.10 or newer was not found. Install Python and add it to PATH.
            exit /b 1
        )
        set "PYTHON=python"
    )
)

%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required to build this application.
    exit /b 1
)

echo Installing application and build dependencies...
%PYTHON% -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    exit /b 1
)

echo Building the Windows executable...
%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --distpath "dist" ^
    --workpath "%TEMP%\Universal_NAND_Flash_Clone_Tool-build" ^
    --specpath "%TEMP%\Universal_NAND_Flash_Clone_Tool-spec" ^
    --icon "%~dp0assets\nand_icon.ico" ^
    --name "Universal NAND Flash Clone Tool" ^
    --add-data "%~dp0assets\nand_icon.svg;assets" ^
    --hidden-import PyQt6.QtSvg ^
    run.py
if errorlevel 1 (
    echo ERROR: PyInstaller failed to build the application.
    exit /b 1
)

echo.
echo Build complete:
echo %~dp0dist\Universal NAND Flash Clone Tool.exe
exit /b 0
