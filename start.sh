#!/bin/bash

# 《顺正理论》资料库启动脚本

echo "🪷 启动《顺正理论》资料库..."
echo ""

# 检查是否在项目根目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 检查后端虚拟环境
if [ ! -d "backend/venv" ]; then
    echo "📦 创建Python虚拟环境..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    source backend/venv/bin/activate
fi

# 检查.env文件
if [ ! -f "backend/.env" ]; then
    echo "⚠️  未找到 backend/.env 文件"
    echo "   请复制 backend/env.example.txt 为 backend/.env 并填入配置"
    exit 1
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 检查向量数据库
if [ ! -d "backend/data/chroma" ]; then
    echo "📚 处理文献数据..."
    cd backend
    python scripts/process_texts.py
    cd ..
fi

echo ""
echo "🚀 启动服务..."
echo ""

# 启动后端
echo "   启动后端服务 (端口 8000)..."
cd backend
# 清除代理环境变量，避免 DeepSeek API 请求超时
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 3

# 启动前端
echo "   启动前端服务 (端口 3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ 服务已启动！"
echo ""
echo "   📖 前端地址: http://localhost:3000"
echo "   🔧 后端API:  http://localhost:8000"
echo "   📚 API文档:  http://localhost:8000/docs"
echo ""
echo "   按 Ctrl+C 停止所有服务"
echo ""

# 捕获退出信号
trap "echo ''; echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# 等待
wait

