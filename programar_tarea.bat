@echo off
:: Programa la tarea de actualización automática en el Programador de tareas de Windows
:: Ejecutar UNA SOLA VEZ como Administrador.

set NOMBRE=GestionLogistica_Actualizador
set SCRIPT=%~dp0actualizar_gestion_logistica.py
set PYTHON=python

echo =====================================================
echo   INVESAKK SAS - Programar Actualizador Logistica
echo =====================================================
echo.
echo Configurando variables de entorno...
setx GL_USUARIO "admin"
setx GL_CLAVE   "admin2026"

echo.
echo Instalando dependencias...
pip install pandas openpyxl pyodbc requests

echo.
echo Creando tarea programada (cada hora, 07:00 - 19:00)...

:: Eliminar si ya existe
schtasks /delete /tn "%NOMBRE%" /f >nul 2>&1

:: Crear tarea: cada hora de lunes a sábado
schtasks /create ^
  /tn "%NOMBRE%" ^
  /tr "%PYTHON% \"%SCRIPT%\"" ^
  /sc HOURLY ^
  /mo 1 ^
  /st 07:00 ^
  /et 19:00 ^
  /k ^
  /d MON,TUE,WED,THU,FRI,SAT ^
  /rl HIGHEST ^
  /f

echo.
echo =====================================================
echo   Tarea creada: %NOMBRE%
echo   Horario: cada hora, 07:00-19:00, Lun-Sab
echo   Log: C:\Automatizaciones\gestion_logistica\log.txt
echo =====================================================
pause
