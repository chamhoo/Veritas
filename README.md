# Veritas - Dynamic Interactive Information Pipeline

An intelligent email-based agent system that monitors various data sources (Reddit, RSS feeds) and notifies users of relevant content based on customizable criteria. The system learns from user feedback to continuously improve its filtering accuracy.

## Features

- **Email-Based Control**: Create, manage, and interact with monitoring tasks entirely through email
- **Multiple Data Sources**: Support for Reddit subreddits and RSS/Atom feeds
- **AI-Powered Filtering**: Uses OpenRouter LLM API to intelligently filter content based on user criteria
- **Interactive Learning**: Refines filtering criteria based on user feedback
- **Microservice Architecture**: Scalable, event-driven design with RabbitMQ messaging

## Architecture

The system consists of 5 microservices:

1. **Mail Gateway**: Polls IMAP inbox for commands and processes user emails
2. **Producer**: Scrapes data sources and publishes new content to the queue
3. **Consumer**: Filters content using LLM and determines relevance
4. **Notifier**: Sends email notifications for relevant content
5. **Feedback Processor**: Refines filtering prompts based on user feedback

## Prerequisites

- Docker and Docker Compose
- Email account with IMAP/SMTP access (Gmail recommended)
- OpenRouter API key ([Get one here](https://openrouter.ai/keys))

## Quick Start

### 1. Clone and Configure

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Configure Environment Variables

Edit the `.env` file with your settings:

```env
# Database (can use defaults)
POSTGRES_DB=pipeline_db
POSTGRES_USER=pipeline_user
POSTGRES_PASSWORD=your_secure_password

# RabbitMQ (can use defaults)
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Email - IMAP (for receiving)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your_agent_email@gmail.com
IMAP_PASSWORD=your_app_password

# Email - SMTP (for sending)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_agent_email@gmail.com
SMTP_PASSWORD=your_app_password

# OpenRouter API
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=openai/gpt-4o-mini

# Intervals
MAIL_POLL_INTERVAL=60
PRODUCER_INTERVAL=300
```

### 3. Gmail App Password Setup

If using Gmail, you need to create an App Password:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification if not already enabled
3. Go to App passwords
4. Generate a new app password for "Mail"
5. Use this password in `IMAP_PASSWORD` and `SMTP_PASSWORD`

### 4. Start the System

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### 5. Verify Services

- RabbitMQ Management: http://localhost:15672 (guest/guest)
- PostgreSQL: localhost:5432

## Usage

### Creating a Monitoring Task

Send an email to your agent's email address:

```
To: your_agent_email@gmail.com
Subject: New Task
Body: monitor the /r/python subreddit for news about web frameworks like Flask or Django
```

### Available Commands

| Subject | Description | Example Body |
|---------|-------------|--------------|
| `New Task` | Create a new monitoring task | `monitor /r/machinelearning for papers about transformers` |
| `List Tasks` | List all your active tasks | (empty or any text) |
| `Pause Task` | Pause a specific task | `123` or `Pause task 123` |
| `Resume Task` | Resume a paused task | `123` |
| `Delete Task` | Delete a task | `123` |

### Providing Feedback

Simply reply to any notification email with feedback:

- "This is not relevant, ignore posts about X"
- "Good match! Show me more content like this"
- "Focus more on Y instead of Z"
- "Too many false positives, be more strict"

The system will automatically refine its filtering criteria based on your feedback.

### Supported Data Sources

**Reddit:**
```
monitor /r/subredditname for [your criteria]
monitor r/python for tutorials about async programming
```

**RSS Feeds:**
```
monitor https://example.com/feed.rss for [your criteria]
monitor RSS: https://news.ycombinator.com/rss for AI startup news
```

## Project Structure

```
veritas/
├── .env.example              # Environment template
├── docker-compose.yml        # Service orchestration
├── README.md                 # This file
├── mail_gateway/             # Email interface service
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── producer/                 # Data scraping service
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── scrapers/
│       ├── __init__.py
│       ├── reddit_scraper.py
│       └── rss_scraper.py
├── consumer/                 # Content filtering service
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── notifier/                 # Email notification service
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── feedback_processor/       # Learning/refinement service
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
└── shared/                   # Shared utilities
    ├── __init__.py
    ├── database.py
    ├── models.py
    └── mq_utils.py
```

## Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check service logs
docker-compose logs mail_gateway
docker-compose logs producer

# Restart specific service
docker-compose restart mail_gateway
```

**Email connection failed:**
- Verify IMAP/SMTP credentials
- Check if app password is correct (Gmail)
- Ensure "Less secure app access" or App Passwords are configured

**No content being processed:**
- Check if tasks are active: send "List Tasks" email
- Verify RabbitMQ queues at http://localhost:15672
- Check producer logs for scraping errors

**OpenRouter API errors:**
- Verify API key is correct
- Check API credits/limits
- Try a different model (e.g., `openai/gpt-3.5-turbo`)

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f consumer

# Last 100 lines
docker-compose logs --tail=100 producer
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it pipeline_postgres psql -U pipeline_user -d pipeline_db

# View tasks
SELECT id, user_email, source_type, status FROM tasks;
```

## Development

### Running Individual Services

```bash
# Install dependencies
pip install -r mail_gateway/requirements.txt

# Set environment variables
export POSTGRES_HOST=localhost
# ... other variables

# Run service
python mail_gateway/main.py
```

### Adding New Scrapers

1. Create a new scraper in `producer/scrapers/`
2. Implement the `scrape(identifier, limit)` method
3. Add the source type to `shared/models.py`
4. Update the producer to use the new scraper

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `MAIL_POLL_INTERVAL` | Seconds between inbox checks | 60 |
| `PRODUCER_INTERVAL` | Seconds between scraping cycles | 300 |
| `OPENROUTER_MODEL` | LLM model to use | openai/gpt-4o-mini |

## Security Notes

- Never commit your `.env` file
- Use app-specific passwords for email
- Rotate your OpenRouter API key periodically
- Use strong database passwords in production

## License

MIT License
