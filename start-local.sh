#!/bin/bash

echo "🚀 Starting SHIRUSHIRU Local Development Environment"
echo "=================================================="

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🔧 Environment Configuration:"
echo "   - Local Backend: http://127.0.0.1:8000"
echo "   - Frontend: http://127.0.0.1:8000"
echo "   - API Mode: Auto-detect (Local for localhost, Dify for production)"
echo ""

echo "🌟 Starting local backend server..."
echo "   - Mock authentication enabled"
echo "   - Streaming chat responses"
echo "   - File upload simulation"
echo "   - Conversation management"
echo ""

node local-backend.js
