@echo off
chcp 65001 >nul
title 《顺正理论》资料库

echo.
echo 🪷 《顺正理论》资料库启动脚本
echo.

:: 检查目录
if not exist "backend" (
    echo ❌ 请在项目根目录运行此脚本
    pause
    exit /b 1
)

:: 检查Python虚拟环境
if not exist "backend\venv" (
    echo 📦 创建Python虚拟环境...
    cd backend
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
) else (
    call backend\venv\Scripts\activate.bat
)

:: 检查.env文件
if not exist "backend\.env" (
    echo ⚠️  未找到 backend\.env 文件
    echo    请复制 backend\env.example.txt 为 backend\.env 并填入配置
    pause
    exit /b 1
)

:: 检查前端依赖
if not exist "frontend\node_modules" (
    echo 📦 安装前端依赖...
    cd frontend
    call npm install
    cd ..
)

:: 检查向量数据库
if not exist "backend\data\chroma" (
    echo 📚 处理文献数据...
    cd backend
    python scripts\process_texts.py
    cd ..
)

echo.
echo 🚀 启动服务...
echo.

:: 启动后端 (新窗口)
start "后端服务" cmd /k "cd backend && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端 (新窗口)
start "前端服务" cmd /k "cd frontend && npm run dev"

echo.
echo ✅ 服务已启动！
echo.
echo    📖 前端地址: http://localhost:3000
echo    🔧 后端API:  http://localhost:8000
echo    📚 API文档:  http://localhost:8000/docs
echo.
echo    关闭此窗口不会停止服务
echo    请手动关闭"后端服务"和"前端服务"窗口来停止服务
echo.

pause

