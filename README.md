# Dynamic Interactive Information Pipeline

An intelligent agent system that monitors content sources and delivers personalized, AI-filtered notifications via email. Users interact with the system entirely through email commands and feedback.

## Overview

This system allows users to:

1. **Create monitoring tasks** by sending an email with their criteria
2. **Receive filtered notifications** when relevant content is found
3. **Refine filtering** by replying to notifications with feedback
4. **Manage tasks** using simple email commands

The system uses AI (via OpenRouter) to intelligently filter content and continuously improve based on user feedback.

## Architecture

The system consists of 6 microservices orchestrated with Docker:

- **Mail Gateway**: Processes email commands and feedback
- **Producer**: Runs scrapers to fetch content from sources (Reddit, RSS)
- **Consumer**: Filters content using LLM
- **Notifier**: Sends email notifications
- **Feedback Processor**: Refines filtering prompts based on user feedback
- **Infrastructure**: PostgreSQL (database) + RabbitMQ (message queue)

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │ Email Commands
       ▼
┌─────────────────┐      ┌──────────────┐
│  Mail Gateway   │◄────►│  PostgreSQL  │
└────────┬────────┘      └──────────────┘
         │
         │ Commands & Feedback
         ▼
    ┌─────────┐
    │RabbitMQ │
    └────┬────┘
         │
    ┌────┴──────────┬──────────┬──────────┐
    ▼               ▼          ▼          ▼
┌──────────┐  ┌──────────┐ ┌─────────┐ ┌─────────────┐
│ Producer │  │ Consumer │ │Notifier │ │  Feedback   │
│          │  │  (LLM)   │ │         │ │  Processor  │
└──────────┘  └──────────┘ └─────────┘ └─────────────┘
```

## Prerequisites

- Docker & Docker Compose
- An email account with IMAP/SMTP access (Gmail recommended)
- OpenRouter API key (https://openrouter.ai/)
- (Optional) Reddit API credentials for Reddit scraping

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd Veritas

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Configure Email

For Gmail:

1. Enable 2-factor authentication on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the app password in `.env` for `EMAIL_PASSWORD` and `SMTP_PASSWORD`

### 3. Get API Keys

**OpenRouter API Key** (Required):
1. Sign up at https://openrouter.ai/
2. Generate an API key
3. Add to `.env` as `OPENROUTER_API_KEY`

**Reddit API** (Optional):
1. Go to https://www.reddit.com/prefs/apps
2. Create an app (select "script")
3. Add credentials to `.env`

### 4. Launch the System

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 5. Verify Setup

```bash
# Check all services are running
docker-compose ps

# View RabbitMQ management UI
# Open http://localhost:15672 (guest/guest)

# Check logs for any errors
docker-compose logs mail_gateway
docker-compose logs producer
docker-compose logs consumer
```

## Usage

### Creating a Monitoring Task

Send an email to your configured address:

```
To: your-email@gmail.com
Subject: New Task
Body: monitor the /r/python subreddit for news about web frameworks
```

You'll receive a confirmation email with your Task ID.

### More Examples

**Monitor RSS Feed:**
```
Subject: New Task
Body: watch RSS feed https://news.ycombinator.com/rss for AI news
```

**Reddit Monitoring:**
```
Subject: New Task
Body: monitor r/machinelearning for papers about reinforcement learning
```

### Managing Tasks

**List All Tasks:**
```
Subject: List Tasks
Body: (empty)
```

**Pause a Task:**
```
Subject: Pause Task 123
Body: (empty)
```

**Resume a Task:**
```
Subject: Resume Task 123
Body: (empty)
```

**Delete a Task:**
```
Subject: Delete Task 123
Body: (empty)
```

### Providing Feedback

When you receive a notification, simply **reply to that email** with your feedback:

```
This is exactly what I'm looking for!
```

```
This is not relevant - I want more technical content
```

```
Too generic, focus on Python-specific frameworks
```

The system will use your feedback to refine the filtering for that task.

## Configuration

### Environment Variables

See `.env.example` for all configuration options.

**Critical Settings:**

| Variable | Description | Required |
|----------|-------------|----------|
| `EMAIL_ADDRESS` | Your email address | Yes |
| `EMAIL_PASSWORD` | Email app password | Yes |
| `SMTP_SERVER` | SMTP server address | Yes |
| `SMTP_USERNAME` | SMTP username | Yes |
| `SMTP_PASSWORD` | SMTP password | Yes |
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes |
| `REDDIT_CLIENT_ID` | Reddit app client ID | No* |
| `REDDIT_CLIENT_SECRET` | Reddit app secret | No* |

\* Required if you want to monitor Reddit

### Customizing Check Intervals

- `POLL_INTERVAL`: How often to check for new emails (default: 60 seconds)
- `PRODUCER_CHECK_INTERVAL`: How often to scrape sources (default: 300 seconds)

## Troubleshooting

### Services Not Starting

```bash
# Check logs for errors
docker-compose logs

# Restart specific service
docker-compose restart mail_gateway

# Rebuild if code changed
docker-compose up -d --build
```

### No Emails Received

1. Check SMTP credentials in `.env`
2. Verify email isn't in spam
3. Check notifier logs: `docker-compose logs notifier`

### No Emails Being Read

1. Verify IMAP credentials in `.env`
2. Check mail_gateway logs: `docker-compose logs mail_gateway`
3. Ensure emails are unread in inbox

### LLM Filtering Not Working

1. Verify `OPENROUTER_API_KEY` is correct
2. Check consumer logs: `docker-compose logs consumer`
3. Ensure you have credits on OpenRouter

### Reddit Scraping Fails

1. Verify Reddit API credentials
2. Check producer logs: `docker-compose logs producer`
3. Ensure Reddit app is configured correctly

## Development

### Project Structure

```
Veritas/
├── shared/                 # Shared utilities
│   ├── database.py         # SQLAlchemy setup
│   ├── models.py           # Database models
│   └── mq_utils.py         # RabbitMQ utilities
├── mail_gateway/           # Email command processor
├── producer/               # Content scraper orchestrator
│   └── scrapers/           # Source-specific scrapers
├── consumer/               # LLM content filter
├── notifier/               # Email notification sender
├── feedback_processor/     # Prompt refinement engine
└── docker-compose.yml      # Service orchestration
```

### Database Schema

**tasks table:**
- `id`: Task ID
- `user_email`: User's email
- `command`: Original command
- `description`: User's monitoring criteria
- `source_type`: "reddit" or "rss"
- `source_params`: JSON with scraper parameters
- `current_prompt`: Current LLM filtering prompt
- `status`: "active", "paused", or "deleted"

**processed_items table:**
- Tracks which content items have been processed
- Prevents duplicate notifications

### Adding New Scrapers

1. Create a new scraper in `producer/scrapers/`
2. Implement `scrape(params)` method
3. Register in `producer/main.py`
4. Update `mail_gateway/main.py` to parse new source type

### Modifying LLM Models

Change `OPENROUTER_MODEL` in `.env`:

```bash
# Use GPT-4
OPENROUTER_MODEL=openai/gpt-4-turbo

# Use Claude Haiku (cheaper)
OPENROUTER_MODEL=anthropic/claude-3-haiku

# Use Llama
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
```

See available models: https://openrouter.ai/models

## Monitoring

### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f consumer

# Last 100 lines
docker-compose logs --tail=100
```

### RabbitMQ Management UI

Access http://localhost:15672

- Username: `guest`
- Password: `guest`

Monitor queues, message rates, and connections.

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d pipeline_db

# View tasks
SELECT id, user_email, status, description FROM tasks;

# View processed items count
SELECT task_id, COUNT(*) FROM processed_items GROUP BY task_id;
```

## Scaling

### Multiple Consumer Instances

To process content faster, scale the consumer:

```bash
docker-compose up -d --scale consumer=3
```

### Multiple Producer Instances

For more frequent scraping:

```bash
docker-compose up -d --scale producer=2
```

## Security Notes

- Never commit `.env` file to version control
- Use app-specific passwords for email
- Rotate API keys regularly
- Consider using secrets management for production
- Monitor OpenRouter API usage to avoid unexpected costs

## Cost Estimation

**OpenRouter API:**
- Claude 3.5 Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- Expected usage: $0.01-0.05 per task per day (depends on content volume)

**Infrastructure:**
- PostgreSQL + RabbitMQ: Self-hosted (free)
- Docker: Free

## License

MIT License - See LICENSE file

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `docker-compose up --build`
5. Submit a pull request

## Support

For issues and questions:
- Open an issue on GitHub
- Check logs: `docker-compose logs`
- Verify `.env` configuration

## Roadmap

- [ ] Web dashboard for task management
- [ ] Support for more sources (Twitter, HackerNews, etc.)
- [ ] Advanced filtering rules (regex, keywords)
- [ ] Email digest mode (daily/weekly summaries)
- [ ] Multi-user support with authentication
- [ ] Webhook notifications
- [ ] Mobile app

## Acknowledgments

- OpenRouter for LLM API access
- Reddit for API access
- Docker and Docker Compose
- PostgreSQL and RabbitMQ teams
