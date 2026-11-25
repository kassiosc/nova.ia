
@echo off
title NOVA AI
color 0B

set "PATH=D:\Users\1080963\node-v26.13.1-win-x64;%PATH%"
set "ROOT=D:\Luan\Projetos Integradores\NOVA-AI"

echo.
echo ========================================
echo             NOVA AI
echo ========================================
echo.

if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo ERRO: ambiente Python nao encontrado.
    pause
    exit /b 1
)

if not exist "%ROOT%\frontend\node_modules" (
    echo ERRO: dependencias do frontend nao encontradas.
    echo Execute npm install na pasta frontend.
    pause
    exit /b 1
)

echo Iniciando backend...
start "NOVA AI - Backend" cmd /k "cd /d ""%ROOT%"" && .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Iniciando frontend...
start "NOVA AI - Frontend" cmd /k "cd /d ""%ROOT%\frontend"" && npm run dev -- --host 127.0.0.1"

timeout /t 5 /nobreak >nul

echo Abrindo NOVA AI...
start http://localhost:5173

echo.
echo NOVA AI iniciada.
echo Mantenha as duas janelas de terminal abertas.
echo.
exit
