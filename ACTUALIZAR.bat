@echo off
chcp 65001 > nul
title Actualizador del bot
cd /d "%~dp0"
echo.
echo  Aplicando el parche y subiendo todo. No cierres esta ventana.
echo.
python actualizar.py %*
if errorlevel 9009 (
  echo.
  echo  [!] Windows no encuentra Python. Instalalo desde python.org
  echo      y marca la casilla "Add Python to PATH".
  pause
)
