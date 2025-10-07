# Quick Reference Guide

## Essential Commands

### Start System
```bash
./start.sh
# OR
docker-compose up -d
```

### Stop System
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f master_bot
docker-compose logs -f producer
docker-compose logs -f consumer
docker-compose logs -f notifier
docker-compose logs -f feedback_processor
```

### Check Status
```bash
docker-compose ps
```

### Restart Service
```bash
docker-compose restart <service_name>
```

### Full Reset (WARNING: Deletes all data)
```bash
docker-compose down -v
```

## Telegram Bot Commands

- `/start` - Welcome message and help
- `/newtask` - Create new monitoring task
- `/listtasks` - View all your tasks
- `/pause <task_id>` - Pause a task
- `/resume <task_id>` - Resume a task
- `/delete <task_id>` - Delete a task

## Management Interfaces

### RabbitMQ Management UI
- URL: http://localhost:15672
- Default credentials: veritas/password (from .env)
- Check queues, message rates, connections

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U veritas -d veritas

# Example queries
SELECT * FROM tasks;
SELECT task_id, source_type, status FROM tasks;
```

## Quick Troubleshooting

### Bot not responding
1. Check if master_bot is running: `docker-compose ps`
2. View logs: `docker-compose logs master_bot`
3. Verify TELEGRAM_BOT_TOKEN in .env

### No notifications
1. Check if content is being scraped: `docker-compose logs producer`
2. Check if filtering is working: `docker-compose logs consumer`
3. Check if notifications are sent: `docker-compose logs notifier`
4. Verify OPENROUTER_API_KEY in .env

### Service crashes
1. Check logs: `docker-compose logs <service>`
2. Restart service: `docker-compose restart <service>`
3. Check if ports are available (5432, 5672, 15672)

## Useful Monitoring Commands

```bash
# Watch logs in real-time
docker-compose logs -f --tail=50

# Check resource usage
docker stats

# Check network connectivity
docker-compose exec master_bot ping -c 3 postgres
docker-compose exec master_bot ping -c 3 rabbitmq

# Execute commands in container
docker-compose exec <service> bash
```

## Configuration Files

- `.env` - Environment variables and secrets
- `docker-compose.yml` - Service orchestration
- `*/requirements.txt` - Python dependencies
- `*/Dockerfile` - Container definitions

## Important Directories

- `shared/` - Common utilities (database, models, MQ client)
- `master_bot/` - Telegram bot interface
- `producer/` - Content scraping service
- `consumer/` - LLM filtering service
- `notifier/` - Telegram notification service
- `feedback_processor/` - Prompt refinement service

## Documentation

- `README.md` - Main documentation with setup and usage
- `TESTING.md` - Comprehensive testing guide and improvements
- `COMPLETION_SUMMARY.md` - Project completion details
- `prompt.txt` - Original requirements specification

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Consult README.md troubleshooting section
3. Check TESTING.md for common issues
4. Review COMPLETION_SUMMARY.md for known limitations

## Next Steps After Setup

1. Configure .env with your tokens
2. Run `./start.sh`
3. Open Telegram bot
4. Send `/start`
5. Create first task with `/newtask`
6. Wait 5-10 minutes for first content
7. Provide feedback on notifications

Enjoy using Veritas! 🚀
