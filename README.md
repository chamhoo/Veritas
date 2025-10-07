# Veritas - Dynamic Interactive Information Pipeline

Veritas is an intelligent agent that monitors information sources and delivers relevant updates via Telegram. Users command the bot in natural language to create monitoring tasks, and the system uses AI (via OpenRouter LLM API) to filter content and adapt to user feedback.

## Features

- 🤖 **Telegram Bot Interface**: Easy-to-use natural language commands
- 🔍 **Multi-Source Monitoring**: Support for Reddit and RSS feeds
- 🧠 **AI-Powered Filtering**: OpenRouter LLM API for intelligent content matching
- 📚 **Adaptive Learning**: User feedback refines filtering criteria over time
- ⚡ **Event-Driven Architecture**: Microservices with RabbitMQ messaging
- 🐳 **Fully Dockerized**: One-command deployment with Docker Compose

## Architecture

The system follows a microservices architecture with the following components:

- **Master Bot**: Telegram interface for user commands and feedback collection
- **Producer**: Periodically scrapes configured sources for new content
- **Consumer**: Filters content using LLM to determine relevance
- **Notifier**: Delivers filtered content to users via Telegram
- **Feedback Processor**: Refines filtering prompts based on user feedback
- **PostgreSQL**: Persistent storage for tasks and configuration
- **RabbitMQ**: Message queue for asynchronous communication

## Prerequisites

- Docker and Docker Compose installed
- Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))
- OpenRouter API Key (sign up at [openrouter.ai](https://openrouter.ai))

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/chamhoo/Veritas.git
cd Veritas
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and set the following required variables:

```bash
# Required: Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Required: Get from openrouter.ai
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Database credentials (defaults provided)
POSTGRES_USER=veritas
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=veritas
DATABASE_URL=postgresql://veritas:your_secure_password@postgres:5432/veritas

# Optional: RabbitMQ credentials (defaults provided)
RABBITMQ_USER=veritas
RABBITMQ_PASSWORD=your_secure_password
RABBITMQ_URL=amqp://veritas:your_secure_password@rabbitmq:5672/
```

### 3. Start the System

```bash
docker-compose up -d
```

This will:
- Pull required Docker images
- Build all service containers
- Initialize the PostgreSQL database
- Start all services in the background

### 4. Verify Services are Running

```bash
docker-compose ps
```

All services should show status "Up" or "Exit 0" (for init_db).

### 5. Check Logs (Optional)

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f master_bot
docker-compose logs -f producer
docker-compose logs -f consumer
```

## Usage Guide

### Starting a Conversation

1. Open Telegram and find your bot (search for the username you set with @BotFather)
2. Send `/start` to begin

### Creating a Monitoring Task

#### Reddit Example:

1. Send `/newtask`
2. Type `reddit` when asked for source type
3. Enter the subreddit name (e.g., `python` for r/python)
4. The bot will confirm task creation

#### RSS Feed Example:

1. Send `/newtask`
2. Type `rss` when asked for source type
3. Enter the RSS feed URL (e.g., `https://hnrss.org/newest`)
4. The bot will confirm task creation

### Managing Tasks

- `/listtasks` - View all your monitoring tasks
- `/pause <task_id>` - Pause a specific task
- `/resume <task_id>` - Resume a paused task
- `/delete <task_id>` - Delete a task permanently

### Providing Feedback

When you receive a notification:
- Click 👍 **Relevant** if the content matches your interests
- Click 👎 **Irrelevant** if the content doesn't match

The system will automatically refine its filtering criteria based on your feedback.

## Service Details

### Master Bot
- Handles Telegram user interactions
- Creates and manages monitoring tasks
- Collects user feedback
- **Default Port**: None (Telegram polling)

### Producer
- Runs every 5 minutes (configurable)
- Scrapes Reddit subreddits and RSS feeds
- Tracks processed items to avoid duplicates
- Publishes new content to RabbitMQ

### Consumer
- Listens for new content from Producer
- Queries OpenRouter API with task-specific prompts
- Filters content based on AI response
- Forwards relevant content to Notifier

### Notifier
- Receives filtered content
- Sends formatted messages to users via Telegram
- Attaches feedback buttons for user interaction

### Feedback Processor
- Receives user feedback from Master Bot
- Uses OpenRouter API to generate improved prompts
- Updates task filtering criteria in database

### Supporting Services

- **PostgreSQL**: Port 5432 (database)
- **RabbitMQ Management UI**: Port 15672 (http://localhost:15672)
  - Default credentials: veritas/password (configurable in .env)

## Configuration Options

### Changing Scraping Frequency

Edit `producer/main.py` line 76:

```python
# Change from 5 minutes to desired interval
schedule.every(5).minutes.do(self.run_tasks)
```

### Changing LLM Model

Edit `consumer/main.py` and `feedback_processor/main.py`:

```python
# Change the model in the API request
"model": "openai/gpt-3.5-turbo"  # Try gpt-4, claude, etc.
```

### Adjusting Log Levels

Set environment variable in `.env`:

```bash
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

## Troubleshooting

### Services Won't Start

1. Check if ports are already in use:
   ```bash
   sudo lsof -i :5432  # PostgreSQL
   sudo lsof -i :5672  # RabbitMQ
   sudo lsof -i :15672 # RabbitMQ Management
   ```

2. Verify environment variables:
   ```bash
   cat .env
   ```

3. Check service logs:
   ```bash
   docker-compose logs <service_name>
   ```

### Bot Not Responding

1. Verify Telegram token is correct
2. Check master_bot logs:
   ```bash
   docker-compose logs -f master_bot
   ```
3. Ensure bot privacy mode is disabled (talk to @BotFather)

### No Notifications Received

1. Check if tasks are active:
   ```bash
   docker-compose logs producer
   ```

2. Verify OpenRouter API key is valid:
   ```bash
   docker-compose logs consumer
   ```

3. Check RabbitMQ queues:
   - Open http://localhost:15672
   - Login with credentials from .env
   - Check "Queues" tab for message flow

### Database Connection Errors

1. Wait for PostgreSQL to fully initialize (can take 30-60 seconds on first run)
2. Check database credentials in .env match docker-compose.yml
3. Restart services:
   ```bash
   docker-compose restart
   ```

## Stopping the System

```bash
# Stop all services (preserves data)
docker-compose down

# Stop and remove all data (complete reset)
docker-compose down -v
```

## Updating the System

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose up -d --build
```

## Project Structure

```
Veritas/
├── docker-compose.yml       # Service orchestration
├── wait-for-it.sh          # Service dependency script
├── init_db.py              # Database initialization
├── .env.example            # Environment template
├── README.md               # This file
├── TESTING.md              # Testing guide
│
├── shared/                 # Shared utilities
│   ├── database.py         # Database connection
│   ├── models.py           # SQLAlchemy models
│   └── mq_utils.py         # RabbitMQ client
│
├── master_bot/             # Telegram bot service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── producer/               # Content scraping service
│   ├── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── scrapers/
│       ├── reddit_scraper.py
│       └── rss_scraper.py
│
├── consumer/               # LLM filtering service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── notifier/               # Telegram notification service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── feedback_processor/     # Prompt refinement service
    ├── main.py
    ├── Dockerfile
    └── requirements.txt
```

## Database Schema

### tasks table

| Column            | Type         | Description                          |
|-------------------|--------------|--------------------------------------|
| task_id           | SERIAL (PK)  | Unique task identifier               |
| user_id           | BIGINT       | Telegram user ID                     |
| telegram_chat_id  | BIGINT       | Chat ID for notifications            |
| source_type       | VARCHAR(50)  | 'reddit' or 'rss'                    |
| source_target     | TEXT         | Subreddit or feed URL                |
| current_prompt    | TEXT         | LLM filtering prompt                 |
| status            | VARCHAR(50)  | 'active' or 'paused'                 |
| created_at        | TIMESTAMP    | Task creation time                   |
| updated_at        | TIMESTAMP    | Last update time                     |

## Message Queue Contracts

### raw_content_queue
Producer → Consumer
```json
{
  "task_id": 123,
  "data": {
    "title": "Post title",
    "url": "https://...",
    "content": "Post content",
    "author": "username",
    "created_utc": 1234567890
  }
}
```

### filtered_content_queue
Consumer → Notifier
```json
{
  "telegram_chat_id": 987654321,
  "formatted_message": "Markdown formatted message",
  "task_id": 123
}
```

### feedback_queue
Master Bot → Feedback Processor
```json
{
  "task_id": 123,
  "feedback_text": "This content is relevant/not relevant",
  "current_prompt": "Current filtering prompt"
}
```

## Technologies Used

- **Language**: Python 3.10+
- **Orchestration**: Docker, Docker Compose
- **Messaging**: RabbitMQ
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI**: OpenRouter API (OpenAI-compatible)
- **Bot Framework**: python-telegram-bot v20+
- **Scraping**: praw (Reddit), feedparser (RSS)

## Contributing

Contributions are welcome! Please see TESTING.md for testing guidelines.

## License

See LICENSE file for details.

## Support

For issues and questions:
1. Check the Troubleshooting section above
2. Review logs: `docker-compose logs -f`
3. Open an issue on GitHub with:
   - Error messages
   - Relevant logs
   - Steps to reproduce

## Roadmap

Potential improvements (see TESTING.md for details):
- [ ] Support for more content sources (Twitter, HackerNews, etc.)
- [ ] Web dashboard for task management
- [ ] Advanced filtering with multiple criteria
- [ ] Content summarization
- [ ] Scheduled digest notifications
- [ ] Multi-language support
- [ ] User authentication and rate limiting
- [ ] Analytics and usage statistics
