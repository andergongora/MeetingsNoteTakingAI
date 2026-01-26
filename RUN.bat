@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Meeting AI System

echo.
echo =====================================================================
echo   MEETING AI SYSTEM
echo =====================================================================
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado
    echo Descargalo desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Ejecutar la aplicación directamente
echo Iniciando Meeting AI System...
echo.
echo Consejos:
echo  - Presiona Ctrl+C para detener la grabacion
echo  - Si falta FFmpeg, instalalo con: winget install ffmpeg
echo  - Si faltan dependencias, instalalo con: pip install -r requirements.txt
echo  - Configura tu GEMINI_API_KEY en el archivo .env
echo.
timeout /t 2 >nul

python main.py

REM Pausar si hay error
if errorlevel 1 (
    echo.
    echo =====================================================================
    echo   Error al ejecutar - Revisa los mensajes de arriba
    echo =====================================================================
    echo.
    pause
)

endlocal
