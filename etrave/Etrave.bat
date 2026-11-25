@echo off
rem Etrave - interface de l EA Strategy V10 (Windows). Double-clic : demarre l interface et ouvre la page dans le navigateur.
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
%PY% etrave\etrave.py %*
if errorlevel 1 pause
