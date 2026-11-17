@echo off
REM Lance le bot BTC en boucle (Windows). Les cles Binance et Telegram doivent etre dans l'environnement (setx).
cd /d "%~dp0\.."
:boucle
python bitcoin\bot.py --config bitcoin\config.json
echo Le bot s'est arrete. Redemarrage dans 60 secondes (Ctrl+C pour quitter)...
timeout /t 60
goto boucle
