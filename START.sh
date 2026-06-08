#!/bin/bash

# Sparrow Detector - Quick Start Script

echo "🐦 Sparrow Detector - Starting..."
echo "================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker found"

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it."
    exit 1
fi

echo "✅ Docker Compose found"

# Build
echo ""
echo "🏗️  Building Docker images (this may take 3-5 minutes)..."
docker compose build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build complete"

# Start
echo ""
echo "🚀 Starting services..."
docker compose up

echo ""
echo "================================"
echo "✅ Services started!"
echo ""
echo "📍 Frontend:  http://localhost"
echo "📍 API Docs:  http://localhost:8000/docs"
echo "📍 API Base:  http://localhost:8000/api"
echo ""
echo "Press Ctrl+C to stop services"
