@echo off
chcp 65001 >nul
title RELATÓRIO TRIMESTRAL — ILHA ECO PASSEIOS
echo.
echo ============================================================
echo   RELATÓRIO EXECUTIVO ILHA ECO — SERVIDOR WEB LOCAL
echo ============================================================
echo.
echo [1/2] Iniciando servidor local na porta 8085...
echo [2/2] Abrindo navegador em http://localhost:8085 ...
echo.

start "" http://localhost:8085

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0servidor_local.ps1" -Port 8085
pause
