@echo off
chcp 65001 >nul
title THE AGENCY — Pipeline dos 7 Agentes Essenciais

echo.
echo ============================================================
echo   THE AGENCY: OS 7 AGENTES QUE VALEM
echo   Baseado em: msitarzewski/agency-agents (150k+ estrelas)
echo   Curadoria:  Fabiano.app
echo ============================================================
echo.

cd /d "%~dp0"
python rodar_agentes.py

echo.
echo ============================================================
echo   Relatório gerado em: CICLO_THE_AGENCY_RELATORIO.md
echo ============================================================
echo.
pause
