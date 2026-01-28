@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Meeting AI System - Setup (Conda)

echo.
echo =====================================================================
echo   MEETING AI SYSTEM - CONFIGURACION INICIAL (CONDA)
echo =====================================================================
echo.

cd /d "%~dp0"

REM ---------------------------------------------------------------------
REM 1. Verificar Conda en PATH
REM ---------------------------------------------------------------------
echo [1/4] Verificando Conda...

where conda >nul 2>&1
if errorlevel 1 (
    echo [X] Conda no esta en el PATH.
    echo Asegurate de marcar "Add Miniconda3 to PATH"
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where conda') do set "CONDA_EXE=%%i"
set "CONDA_ROOT=%CONDA_EXE%\..\.."
set "CONDA_BAT=%CONDA_ROOT%\condabin\conda.bat"

if not exist "%CONDA_BAT%" (
    echo [X] No se encontro conda.bat
    echo Ruta esperada: %CONDA_BAT%
    pause
    exit /b 1
)

call "%CONDA_BAT%" --version >nul 2>&1
if errorlevel 1 (
    echo [X] Error inicializando conda.bat
    pause
    exit /b 1
)
echo [OK] Conda detectado.

REM ---------------------------------------------------------------------
REM 2. Configuracion .env
REM ---------------------------------------------------------------------
echo.
echo [2/4] Configuracion (.env)

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
    echo 1. Ve a https://makersuite.google.com/app/apikey
    echo 2. Crea la API key
    echo 3. Pegala en el archivo .env
    echo.
    choice /C SN /N /M "Abrir .env ahora? (S=si, N=no): "
    if not errorlevel 2 (
        notepad ".env"
        pause
    )
) else (
    echo [OK] GEMINI_API_KEY configurada
)

REM ---------------------------------------------------------------------
REM 3. Crear / actualizar entorno Conda
REM ---------------------------------------------------------------------
echo.
echo [3/4] Creando / actualizando entorno Conda 'meetingsnotetakingai'
echo Esto puede tardar varios minutos...
echo.

call "%CONDA_BAT%" env update -n meetingsnotetakingai --file environment.yml --prune
if errorlevel 1 (
    echo [X] Error actualizando el entorno Conda
    pause
    exit /b 1
)

call "%CONDA_BAT%" activate meetingsnotetakingai
if errorlevel 1 (
    echo [X] No se pudo activar el entorno Conda
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set "PYVER=%%V"
echo Python detectado: %PYVER%

echo %PYVER% | findstr "^3\.10\." >nul || (
    echo [X] Se requiere Python 3.10.x
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------
REM 4. Instalacion pip (orden seguro CUDA)
REM ---------------------------------------------------------------------
echo.
echo [4/4] Instalando dependencias pip

python -m pip install --upgrade pip
if errorlevel 1 (
    echo [X] Error actualizando pip
    pause
    exit /b 1
)

REM ---- PyTorch CUDA ----
echo.
echo Instalando PyTorch CUDA 12.9...
pip install "torch==2.8.0+cu129" "torchvision==0.23.0+cu129" "torchaudio==2.8.0" --index-url https://download.pytorch.org/whl/cu129
if errorlevel 1 (
    echo [X] Error instalando PyTorch CUDA. Si falla, prueba la variante CPU o revisa drivers NVIDIA.
    pause
    exit /b 1
)

REM Verificacion simple de torch y CUDA
python -c "import torch; print('torch:', getattr(torch,'__version__','<missing>')); print('CUDA disponible:', torch.cuda.is_available())"

REM ---- pyannote (sin deps) ----
echo.
echo Instalando pyannote.audio (sin deps)...
pip install pyannote.audio==4.0.3 --no-deps
if errorlevel 1 (
    echo [X] Error instalando pyannote.audio --no-deps
    pause
    exit /b 1
)

REM ---- ffmpeg (conda) ----
echo.
echo Instalando ffmpeg via conda (si es necesario)...
call "%CONDA_BAT%" install -n meetingsnotetakingai -y "ffmpeg<8" >nul 2>&1

REM ---- resto de deps (excluir torch / pyannote) ----
set "REQ_TMP=%TEMP%\req_no_torch.txt"
findstr /v /b /c:"torch==" /c:"torchvision==" /c:"torchaudio==" /c:"pyannote.audio==" requirements.txt > "%REQ_TMP%"

echo.
echo Instalando el resto de dependencias pip...
pip install -r "%REQ_TMP%"
if errorlevel 1 (
    echo [X] Error instalando dependencias pip desde %REQ_TMP%
    del "%REQ_TMP%" >nul 2>&1
    pause
    exit /b 1
)
del "%REQ_TMP%" >nul 2>&1

REM ---- Comprobacion final CUDA (usando python -c) ----
python -c "import torch,sys; sys.exit(0) if torch.cuda.is_available() else sys.exit(1)"
if errorlevel 1 (
    echo CUDA NO disponible. Reinstalando torch+cu129...
    pip install --force-reinstall "torch==2.8.0+cu129" "torchvision==0.23.0+cu129" "torchaudio==2.8.0" --index-url https://download.pytorch.org/whl/cu129
    if errorlevel 1 (
        echo [X] Reinstalacion forzada de torch fallo. Verifica drivers CUDA y compatibilidad.
        pause
        exit /b 1
    )
)

echo.
echo =====================================================================
echo   CONFIGURACION COMPLETADA CORRECTAMENTE
echo =====================================================================
echo.
echo Para iniciar la aplicacion:
echo   Ejecuta RUN.bat
echo.
pause
endlocal
