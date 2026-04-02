@echo off
title Sistema Unificado Santo Tomas / PeYa
setlocal

:: Cambia al directorio donde esta el archivo .bat
cd /d "%~dp0"

echo [1/2] Buscando entorno virtual...

:: Intentar activar el entorno 'env' o 'venv'
if exist env\Scripts\activate (
    call env\Scripts\activate
) else if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo [AVISO] No se encontro entorno 'env'. Usando Python global...
)

echo [2/2] Iniciando aplicacion unificada...
echo ---------------------------------------
:: Ejecutar la aplicacion unificada
streamlit run app_unificada.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo iniciar Streamlit.
    echo Asegurate de tener instaladas las librerias:
    echo pip install streamlit pandas openpyxl fpdf
    pause
)