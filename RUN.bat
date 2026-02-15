@echo off
setlocal
chcp 65001 >nul 2>&1
title Meeting AI System

echo.
echo =====================================================================
echo   MEETING AI SYSTEM
echo =====================================================================
echo.

cd /d "%~dp0"

set "ENV_NAME=meetingsnotetakingai"

REM --------------------------------------------------
REM Detectar conda.bat
REM --------------------------------------------------
where conda >nul 2>&1 || (
    echo [ERROR] Conda no esta en el PATH.
    echo Ejecuta primero SETUP.bat.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where conda') do set "CONDA_EXE=%%i"
set "CONDA_ROOT=%CONDA_EXE%\..\.."
set "CONDA_BAT=%CONDA_ROOT%\condabin\conda.bat"

if not exist "%CONDA_BAT%" (
    echo [ERROR] No se encontro conda.bat
    echo Ruta esperada: %CONDA_BAT%
    pause
    exit /b 1
)

REM --------------------------------------------------
REM Activar entorno
REM --------------------------------------------------
call "%CONDA_BAT%" activate %ENV_NAME%
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno %ENV_NAME%
    pause
    exit /b 1
)

echo Entorno activo: %CONDA_DEFAULT_ENV%
python --version
echo.

REM --------------------------------------------------
REM Ejecutar aplicacion
REM --------------------------------------------------
echo Iniciando aplicacion...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo =====================================================================
    echo   ERROR AL EJECUTAR LA APLICACION
    echo =====================================================================
    echo.
    pause
)

endlocal
