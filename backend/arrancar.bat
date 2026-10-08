@echo off
title INVESAKK - Gestion Logistica
echo ============================================
echo   INVESAKK SAS - Gestion Logistica
echo   NIT 802014471-6 - Barranquilla, Colombia
echo ============================================
echo.
echo Iniciando servidor...
echo Accede en: http://localhost:5000
echo.
echo Credenciales:
echo   Admin:  admin / admin2026
echo   Jefe:   jefe.logistica / jefe2026
echo   Conductor ejemplo: roa.julio / roa2026
echo.
echo Presiona Ctrl+C para detener.
echo ============================================
cd /d "%~dp0"
python app.py
pause
