@echo off
title Lanzador de Calendario (Entorno Virtual)
setlocal

:: Cambia al directorio donde está el archivo .bat
cd /d "%~dp0"

echo Buscando entorno virtual...

:: Verifica si existe la carpeta 'env' o 'venv' y la activa
if exist env\Scripts\activate (
    echo Activando entorno 'env'...
    call env\Scripts\activate
) else if exist venv\Scripts\activate (
    echo Activando entorno 'venv'...
    call venv\Scripts\activate
) else (
    echo [ADVERTENCIA] No se encontro la carpeta 'env' o 'venv'. 
    echo Intentando ejecutar con el Python global...
    echo.
)

echo Iniciando Streamlit...
streamlit run horarios.py

:: Si hay un error, la ventana no se cierra para que puedas leerlo
if %errorlevel% neq 0 (
    echo.
    echo Ocurrio un error al iniciar la aplicacion.
    pause
)