#!/bin/bash
# Quick start script for Veritas

set -e

echo "🚀 Veritas - Dynamic Interactive Information Pipeline"
echo "================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your credentials:"
    echo "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo "   - OPENROUTER_API_KEY (get from openrouter.ai)"
    echo ""
    read -p "Press Enter after you've configured .env, or Ctrl+C to exit..."
fi

# Validate required environment variables
echo "🔍 Validating environment variables..."
source .env

if [ "$TELEGRAM_BOT_TOKEN" = "your_telegram_bot_token_here" ] || [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN not configured in .env"
    exit 1
fi

if [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ] || [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ Error: OPENROUTER_API_KEY not configured in .env"
    exit 1
fi

echo "✅ Environment variables configured"
echo ""

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Veritas is starting!"
echo ""
echo "📝 Next Steps:"
echo "  1. Check logs: docker-compose logs -f"
echo "  2. Open Telegram and find your bot"
echo "  3. Send /start to begin"
echo "  4. Create your first task with /newtask"
echo ""
echo "🔗 Useful Links:"
echo "  - RabbitMQ Management: http://localhost:15672"
echo "  - Documentation: README.md"
echo "  - Testing Guide: TESTING.md"
echo ""
echo "🛠️  Useful Commands:"
echo "  - View logs: docker-compose logs -f [service_name]"
echo "  - Restart: docker-compose restart"
echo "  - Stop: docker-compose down"
echo "  - Full reset: docker-compose down -v"
echo ""
