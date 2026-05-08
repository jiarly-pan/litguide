@echo off
chcp 65001 >nul
title 文献检索指导系统
set PYTHONUTF8=1
python -m litguide.gui
pause
