@echo off
title MoliyaAI Launcher
echo ===================================================
echo ⚡ MoliyaAI Web Server va Telegram Bot Launcher ⚡
echo ===================================================
echo.
echo [1/2] Django Web Serverni ishga tushirish...
start "MoliyaAI Web Server" cmd /k ".venv\Scripts\python manage.py runserver"

echo [2/2] Telegram Botni ishga tushirish...
start "MoliyaAI Telegram Bot" cmd /k ".venv\Scripts\python bot.py"

echo.
echo ===================================================
echo ✅ Ikkala tizim ham alohida konsollarda ishga tushdi!
echo ===================================================
pause
