@echo off
rem Quitte le Bureau a distance SANS fermer la session : l ecran du VPS reste actif, MetaTrader continue, et la photo du soir
rem de l onglet Historique (outil video) n est pas noire. A lancer en administrateur (clic droit, Executer en tant qu administrateur).
for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (%windir%\System32\tscon.exe %%s /dest:console)
