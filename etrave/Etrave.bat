@echo off
rem Etrave - interface de l EA Strategy V11 (Windows). Double-clic : met l EA et ses deux graphiques a jour, ouvre MetaTrader 5 et la page.
chcp 65001 >nul
title Etrave
cd /d "%~dp0.."
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
rem ET-15 : sous Windows 10/11 sans Python, "python" est un raccourci vers le Microsoft Store qui ne lance rien : on l essaie.
if defined PY %PY% -c "import sys" >nul 2>nul || set PY=
if not defined PY (
  echo Python n est pas installe sur cet ordinateur.
  echo Installe-le depuis https://www.python.org/downloads/ en cochant "Add python.exe to PATH",
  echo puis double-clique a nouveau sur Etrave.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)
rem Double-clic : ouvre aussi MetaTrader 5 (V11 sur le Nasdaq et le S&P 500). Au demarrage de Windows (--sans-navigateur) : seulement si la case est cochee.
if /i "%~1"=="--sans-navigateur" (%PY% etrave\etrave.py %*) else (%PY% etrave\etrave.py --tout %*)
if errorlevel 1 pause
