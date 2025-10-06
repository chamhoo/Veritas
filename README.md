# Veritas

Veritas is a Dynamic Interactive Information Pipeline that acts as an intelligent agent users can command via Telegram. It monitors specified information sources, intelligently filters content, and delivers relevant updates to users.

## Architecture

The system follows a microservices architecture:

- **Master Bot**: Telegram interface for user commands and feedback
- **Producer**: Manages data scrapers and collects new content
- **Consumer**: Filters content using LLM to determine relevance
- **Notifier**: Delivers filtered content to users via Telegram
- **Feedback Processor**: Refines filtering criteria based on user feedback

## Technologies

- Python 3.10+
- Docker and Docker Compose
- RabbitMQ for messaging
- PostgreSQL for persistent storage
- OpenRouter API for LLM capabilities

## Setup

1. Clone this repository
2. Copy `.env.example` to `.env` and fill in the required environment variables
3. Run `docker-compose up -d` to start the services

## Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `DATABASE_URL`: PostgreSQL connection string
- `RABBITMQ_URL`: RabbitMQ connection string

## Structure

```
Veritas/
├── .env.example         # Environment variables template
├── docker-compose.yml   # Service orchestration
├── README.md            # This file
├── master_bot/          # Telegram bot interface
├── producer/            # Content scraping service
├── consumer/            # LLM-based content filtering
├── notifier/            # User notification service
├── feedback_processor/  # Feedback processing service
└── shared/              # Shared utilities
```
