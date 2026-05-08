@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ╔══════════════════════════════════════════════╗
echo ║    文献检索指导系统 Web 版 v2.0               ║
echo ║    访问地址: http://127.0.0.1:5000            ║
echo ╚══════════════════════════════════════════════╝
echo.
echo   主页 (检索策略): http://127.0.0.1:5000/
echo   文献检索:       http://127.0.0.1:5000/literature
echo.
echo 按 Ctrl+C 停止服务器
echo.

python -m litguide
pause
