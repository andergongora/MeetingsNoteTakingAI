@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Meeting AI System - Setup

echo.
echo =====================================================================
echo   MEETING AI SYSTEM - CONFIGURACION INICIAL
echo =====================================================================
echo.

cd /d "%~dp0"

echo Este script te ayudara a configurar todo lo necesario.
echo.
pause

REM 1. Verificar Python
echo.
echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python no esta instalado
    echo.
    echo Por favor instala Python 3.13+ desde:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo [OK] Python encontrado
python --version

REM 2. Instalar FFmpeg
echo.
echo [2/4] FFmpeg (necesario para transcripcion)
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [!] FFmpeg no encontrado
    echo.
    choice /C SN /N /M "Instalar FFmpeg con winget? (S=si, N=no): "
    if not errorlevel 2 (
        winget install --id Gyan.FFmpeg -e
        echo [OK] FFmpeg instalado
    ) else (
        echo [!] Saltado - Instalalo manualmente despues
    )
) else (
    echo [OK] FFmpeg ya instalado
)

REM 3. Configurar .env
echo.
echo [3/4] Configuracion (.env)
if not exist ".env" (
    if exist ".env.template" (
        copy ".env.template" ".env" >nul
        echo [OK] Archivo .env creado
    )
)

findstr /C:"GEMINI_API_KEY=your_gemini_api_key_here" .env >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [!] Necesitas configurar tu GEMINI_API_KEY
    echo.
    echo 1. Ve a: https://makersuite.google.com/app/apikey
    echo 2. Crea tu API key gratis
    echo 3. Pegala en el archivo .env
    echo.
    choice /C SN /N /M "Abrir .env ahora? (S=si, N=no): "
    if not errorlevel 2 (
        notepad ".env"
        echo.
        echo [OK] Guarda el archivo cuando hayas pegado tu API key
        pause
    )
) else (
    echo [OK] GEMINI_API_KEY configurada
)

REM 4. Instalar dependencias Python
echo.
echo [4/4] Dependencias de Python
python -c "import pyaudiowpatch" >nul 2>&1
if errorlevel 1 (
    echo [!] Dependencias no instaladas
    echo.
    echo NOTA: Esto descargara ~2GB y puede tomar 5-10 minutos
    echo.
    choice /C SN /N /M "Instalar dependencias ahora? (S=si, N=no): "
    if not errorlevel 2 (
        echo.
        echo Instalando... Por favor espera...
        python -m pip install --upgrade pip --quiet
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [X] Error instalando dependencias
            pause
            exit /b 1
        )
        echo [OK] Dependencias instaladas
    ) else (
        echo [!] Saltado - Instalalas con: pip install -r requirements.txt
    )
) else (
    echo [OK] Dependencias ya instaladas
)

echo.
echo =====================================================================
echo   CONFIGURACION COMPLETADA
echo =====================================================================
echo.
echo Ahora puedes ejecutar RUN.bat para iniciar la aplicacion
echo.
pause

endlocal
