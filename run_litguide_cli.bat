@echo off
chcp 65001 >nul
title 文献检索指导系统 - 命令行模式
set PYTHONUTF8=1
echo.
echo   ========================================
echo     文献检索指导系统 - 命令行模式
echo   ========================================
echo.
echo   用法:
echo     litguide search "研究主题" -t 文献类型
echo.
echo   文献类型: 综述型 / 应用型 / 前沿型 / 对比型
echo.
echo   示例:
echo     litguide search "机器学习" -t 综述型
echo.
echo   其他命令:
echo     litguide types      查看权重说明
echo     litguide history    查看检索历史
echo     litguide reset      重置会话
echo.
echo   ========================================
echo.
set /p topic="请输入研究主题: "
set /p ptype="请输入文献类型 (综述型/应用型/前沿型/对比型, 默认综述型): "
if "%ptype%"=="" set ptype=综述型
echo.
litguide search "%topic%" -t "%ptype%"
echo.
pause
