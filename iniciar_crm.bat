@echo off
chcp 65001 >nul
title PROPEL CRM — Mesa de Operações Comerciais

echo.
echo ============================================================
echo   PROPEL AGENTES — PLATAFORMA COMERCIAL (CRM KANBAN)
echo ============================================================
echo.
echo [1/2] Iniciando servidor local do CRM...

cd /d "%~dp0propel_crm"

REM Inicia o servidor em segundo plano e abre o navegador
start "" http://127.0.0.1:8000

echo [2/2] Servidor ativo em: http://127.0.0.1:8000
echo.
echo ============================================================
echo   Login padrão:
echo   Usuário: propel
echo   Senha:   propel2027
echo ============================================================
echo.
echo Para fechar a plataforma, basta fechar esta janela.
echo.

python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
