@echo off
chcp 65001 >nul
title PROPEL AGENTES — Módulo 2: Inteligência Comercial

echo.
echo ============================================================
echo   PROPEL AGENTES — MÓDULO 2: SCRAPER DE LEADS DE TURISMO
echo ============================================================
echo.

REM Verifica se Python está instalado
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python não encontrado. Instale pelo site python.org
    pause
    exit /b 1
)

REM Instala dependências se necessário
echo [1/3] Verificando dependências...
python -m pip install requests beautifulsoup4 ddgs --quiet --disable-pip-version-check
echo       OK.

REM Cria pasta de outputs
if not exist "outputs" mkdir outputs

REM Executa o pipeline completo
echo [2/3] Iniciando coleta de leads...
echo       (Isso pode levar 5-15 minutos dependendo da quantidade de nichos)
echo.
python main.py 2^>^&1

echo.
echo [3/3] Abrindo relatório de leads qualificados...
if exist "outputs\LEADS_QUALIFICADOS.md" (
    start "" "outputs\LEADS_QUALIFICADOS.md"
) else (
    echo [AVISO] Relatório não gerado. Verifique o log em outputs\log_execucao.txt
)

echo.
echo ============================================================
echo   Processo concluído! Verifique a pasta outputs\
echo ============================================================
echo.
pause
