@echo off
title Compilando a Ejecutable
echo Activando entorno...

call env\Scripts\activate

echo Iniciando compilacion con PyInstaller...
:: --onefile: crea un solo archivo
:: --additional-hooks-dir: ayuda a PyInstaller a entender Streamlit
pyinstaller --noconfirm --onefile --windowed --collect-all streamlit --collect-all pandas --add-data "horarios.db;." horarios.py

echo.
echo Proceso finalizado. Busca tu archivo en la carpeta 'dist'.
pause