# Veritas Testing Guide

This document provides comprehensive testing instructions for the Veritas Dynamic Interactive Information Pipeline system, along with suggestions for future improvements.

## Table of Contents

1. [Pre-Testing Setup](#pre-testing-setup)
2. [Manual Testing Procedures](#manual-testing-procedures)
3. [Component Testing](#component-testing)
4. [Integration Testing](#integration-testing)
5. [Common Issues and Solutions](#common-issues-and-solutions)
6. [Performance Testing](#performance-testing)
7. [Future Improvements](#future-improvements)

---

## Pre-Testing Setup

### 1. Environment Preparation

Before testing, ensure you have:

- [ ] Docker and Docker Compose installed and running
- [ ] Valid Telegram Bot Token from [@BotFather](https://t.me/botfather)
- [ ] Valid OpenRouter API Key from [openrouter.ai](https://openrouter.ai)
- [ ] `.env` file configured with all required credentials
- [ ] At least 2GB of free RAM
- [ ] Ports 5432, 5672, and 15672 available

### 2. Initial System Startup

```bash
# Navigate to project directory
cd /path/to/Veritas

# Start all services
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check logs for errors
docker-compose logs -f
```

Expected output: All services should show "Up" status (except init_db which should show "Exit 0").

### 3. Verify Database Initialization

```bash
# Check init_db logs
docker-compose logs init_db

# Expected: "Database initialization complete!"
```

### 4. Verify RabbitMQ

1. Open http://localhost:15672 in your browser
2. Login with credentials from `.env` (default: veritas/password)
3. Navigate to "Queues" tab
4. Verify these queues exist:
   - `raw_content_queue`
   - `filtered_content_queue`
   - `feedback_queue`

---

## Manual Testing Procedures

### Test Case 1: Bot Connection

**Objective**: Verify the Telegram bot is responsive

**Steps**:
1. Open Telegram and search for your bot
2. Send `/start` command

**Expected Result**:
```
Welcome to Veritas! I can monitor information sources for you.

Use /newtask to create a new monitoring task.
Use /listtasks to see your current tasks.
Use /pause <task_id> to pause a task.
Use /resume <task_id> to resume a paused task.
Use /delete <task_id> to delete a task.
```

**Troubleshooting**:
- If no response: Check `docker-compose logs master_bot`
- Verify `TELEGRAM_BOT_TOKEN` in `.env`
- Ensure bot privacy mode is disabled with @BotFather

---

### Test Case 2: Create Reddit Task

**Objective**: Test task creation for Reddit source

**Steps**:
1. Send `/newtask` to bot
2. Reply with `reddit`
3. Reply with `python` (or another active subreddit)

**Expected Result**:
```
Task #1 created successfully!
I will monitor reddit source 'python' for new content.
```

**Verification**:
```bash
# Check database
docker-compose exec postgres psql -U veritas -d veritas -c "SELECT * FROM tasks;"

# Expected: One row with source_type='reddit', source_target='python'
```

**Troubleshooting**:
- If no response: Check master_bot logs
- If database error: Check postgres logs

---

### Test Case 3: Create RSS Task

**Objective**: Test task creation for RSS source

**Steps**:
1. Send `/newtask` to bot
2. Reply with `rss`
3. Reply with `https://hnrss.org/newest` (HackerNews RSS)

**Expected Result**:
```
Task #2 created successfully!
I will monitor rss source 'https://hnrss.org/newest' for new content.
```

**Verification**:
```bash
# Check database
docker-compose exec postgres psql -U veritas -d veritas -c "SELECT task_id, source_type, source_target FROM tasks;"
```

---

### Test Case 4: List Tasks

**Objective**: Verify task listing functionality

**Steps**:
1. Send `/listtasks` to bot

**Expected Result**:
```
Your tasks:

✅ Task #1: reddit - python
✅ Task #2: rss - https://hnrss.org/newest
```

---

### Test Case 5: Producer Scraping

**Objective**: Verify producer collects content

**Wait**: 5-10 minutes for first scraping cycle

**Verification**:
```bash
# Check producer logs
docker-compose logs producer | grep "Found"

# Expected output like:
# "Found 5 new items for task 1"
# "Found 3 new items for task 2"

# Check RabbitMQ queue
# raw_content_queue should have messages
```

**Manual Trigger** (for immediate testing):
```bash
# Restart producer to trigger immediate scrape
docker-compose restart producer
```

---

### Test Case 6: Consumer Filtering

**Objective**: Verify LLM filtering works

**Prerequisites**: Test Case 5 completed (content in queue)

**Verification**:
```bash
# Check consumer logs
docker-compose logs consumer | grep "relevant"

# Expected outputs:
# "Content is relevant for task X"
# "Content is not relevant for task X"
# "Published notification for task X"
```

**Check OpenRouter API calls**:
```bash
docker-compose logs consumer | grep "OpenRouter"

# Should NOT see errors unless API key is invalid
```

---

### Test Case 7: Receive Notifications

**Objective**: Verify notifications arrive in Telegram

**Prerequisites**: Test Cases 5-6 completed

**Expected Result**:
- Receive Telegram message(s) with:
  - Title of content
  - Summary/excerpt
  - Source information
  - "Read more" link
  - Feedback buttons (👍 Relevant / 👎 Irrelevant)

**Verification**:
```bash
# Check notifier logs
docker-compose logs notifier | grep "Sent notification"
```

**Troubleshooting**:
- If no notifications after 10 minutes:
  1. Check if consumer filtered content as relevant
  2. Check notifier logs for errors
  3. Verify bot can send messages (test with /start)

---

### Test Case 8: Feedback Collection

**Objective**: Test user feedback mechanism

**Steps**:
1. Click 👍 **Relevant** or 👎 **Irrelevant** on a notification
2. Observe message update

**Expected Result**:
- Message updates to show: "✅ Feedback received: Relevant" (or Irrelevant)

**Verification**:
```bash
# Check master_bot logs
docker-compose logs master_bot | grep "feedback"

# Check RabbitMQ feedback_queue has messages
```

---

### Test Case 9: Prompt Refinement

**Objective**: Verify feedback processor updates prompts

**Prerequisites**: Test Case 8 completed (feedback submitted)

**Verification**:
```bash
# Check feedback_processor logs
docker-compose logs feedback_processor | grep "Updated prompt"

# Check database - prompt should be different now
docker-compose exec postgres psql -U veritas -d veritas -c "SELECT task_id, current_prompt FROM tasks;"
```

**Compare**: The `current_prompt` should reflect the feedback (more specific based on what was marked relevant/irrelevant)

---

### Test Case 10: Task Management

**Objective**: Test pause/resume/delete functionality

**Steps**:
1. Send `/pause 1` to bot
2. Send `/listtasks` - verify task shows ⏸️
3. Send `/resume 1` to bot
4. Send `/listtasks` - verify task shows ✅
5. Send `/delete 2` to bot
6. Send `/listtasks` - verify task 2 is gone

**Verification**:
```bash
# Check database after each operation
docker-compose exec postgres psql -U veritas -d veritas -c "SELECT task_id, status FROM tasks;"
```

---

## Component Testing

### Testing Individual Services

#### Test Master Bot Alone

```bash
# Stop all services
docker-compose down

# Start only required services
docker-compose up -d postgres rabbitmq init_db
docker-compose up master_bot

# Test bot commands
# Logs: docker-compose logs -f master_bot
```

#### Test Producer Alone

```bash
# Start dependencies
docker-compose up -d postgres rabbitmq init_db

# Create test task manually
docker-compose exec postgres psql -U veritas -d veritas -c "
INSERT INTO tasks (user_id, telegram_chat_id, source_type, source_target, current_prompt, status)
VALUES (123456, 123456, 'reddit', 'python', 'Test prompt', 'active');"

# Start producer
docker-compose up producer

# Check logs for scraping
docker-compose logs -f producer
```

#### Test Consumer Alone

```bash
# Start dependencies
docker-compose up -d postgres rabbitmq init_db

# Publish test message to raw_content_queue
docker-compose exec rabbitmq rabbitmqadmin publish routing_key=raw_content_queue payload='{"task_id":1,"data":{"title":"Test","url":"http://test.com","content":"Python testing"}}'

# Start consumer
docker-compose up consumer

# Check if it processes the message
docker-compose logs -f consumer
```

---

## Integration Testing

### End-to-End Test Scenario

**Objective**: Full user journey from task creation to feedback

**Duration**: ~15-20 minutes

**Steps**:

1. **Setup** (2 min)
   ```bash
   docker-compose up -d
   ```

2. **Create Task** (1 min)
   - `/newtask` → `reddit` → `programming`

3. **Wait for Content** (10 min)
   - Monitor logs: `docker-compose logs -f producer consumer notifier`

4. **Receive Notification** (immediate when content found)
   - Verify notification format
   - Verify buttons work

5. **Provide Feedback** (1 min)
   - Click 👍 or 👎
   - Verify acknowledgment

6. **Verify Refinement** (2 min)
   ```bash
   # Check prompt was updated
   docker-compose logs feedback_processor
   ```

7. **Verify Improved Filtering** (wait for next content cycle)
   - Observe if subsequent notifications better match your preference

**Success Criteria**:
- ✅ Task created successfully
- ✅ Content scraped within 10 minutes
- ✅ At least one notification received
- ✅ Feedback acknowledged
- ✅ Prompt updated in database

---

## Common Issues and Solutions

### Issue 1: Services Won't Start

**Symptoms**: `docker-compose up` fails or services exit immediately

**Solutions**:
```bash
# Check if ports are in use
sudo lsof -i :5432
sudo lsof -i :5672

# Check disk space
df -h

# Rebuild images
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue 2: No Content Being Scraped

**Symptoms**: Producer logs show "Found 0 new items"

**Possible Causes**:
- Subreddit name typo (should be `python`, not `r/python`)
- RSS feed is down or invalid
- Content already processed (IDs cached in memory)

**Solutions**:
```bash
# Restart producer to clear in-memory cache
docker-compose restart producer

# Try a very active subreddit
# /newtask → reddit → AskReddit

# Try a reliable RSS feed
# /newtask → rss → https://hnrss.org/newest
```

### Issue 3: Consumer Not Filtering

**Symptoms**: Consumer logs show errors, no notifications sent

**Check**:
```bash
docker-compose logs consumer | grep -i error
```

**Common Issues**:
- Invalid OpenRouter API key
- API rate limit exceeded
- Network connectivity issues

**Solutions**:
```bash
# Verify API key
echo $OPENROUTER_API_KEY

# Test API manually
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-3.5-turbo","messages":[{"role":"user","content":"test"}]}'

# Check consumer container network
docker-compose exec consumer ping -c 3 google.com
```

### Issue 4: Notifications Not Arriving

**Symptoms**: Consumer says "Published notification" but nothing in Telegram

**Check**:
```bash
docker-compose logs notifier | grep -i error
```

**Solutions**:
- Verify bot token: Send `/start` to bot
- Check if bot was blocked by user
- Verify chat_id matches in database:
  ```bash
  docker-compose exec postgres psql -U veritas -d veritas -c "SELECT telegram_chat_id FROM tasks;"
  ```

### Issue 5: Feedback Not Working

**Symptoms**: Clicking buttons does nothing

**Solutions**:
- Check if master_bot is running: `docker-compose ps`
- Verify callback handler is registered (check master_bot logs on startup)
- Test with fresh notification

---

## Performance Testing

### Load Testing

**Test 1: Multiple Tasks**
```bash
# Create 10 tasks quickly
# Monitor resource usage
docker stats

# Expected: <1GB RAM total, <10% CPU per service
```

**Test 2: High-Volume Content**
```bash
# Create task for very active source
# /newtask → reddit → AskReddit

# Monitor queue depth
# RabbitMQ UI → Queues → Check message rates
```

**Test 3: Concurrent Users**
- Have 3-5 users create tasks simultaneously
- Verify database transactions don't conflict
- Check response times remain acceptable (<5 seconds)

### Benchmarks (Expected Performance)

| Metric | Expected Value | Concerning If |
|--------|----------------|---------------|
| Task Creation | <3 seconds | >10 seconds |
| Content Scraping | Every 5 minutes | >10 minutes between cycles |
| LLM Filtering | <10 seconds/item | >30 seconds/item |
| Notification Delivery | <5 seconds | >15 seconds |
| Memory Usage (total) | <1GB | >2GB |
| CPU Usage (idle) | <5% | >20% |

---

## Future Improvements

### Priority 1: Critical Features

1. **Persistent Scraper State**
   - **Issue**: Scrapers lose processed IDs on restart
   - **Solution**: Store processed item IDs in database
   - **Files to modify**: `producer/scrapers/*.py`, add new table `processed_items`

2. **Better Error Recovery**
   - **Issue**: Services crash on unhandled exceptions
   - **Solution**: Implement comprehensive try-catch and restart policies
   - **Files to modify**: All `main.py` files, add global exception handlers

3. **Rate Limiting**
   - **Issue**: Could exceed API limits with many tasks
   - **Solution**: Implement token bucket algorithm for OpenRouter API
   - **Files to modify**: `consumer/main.py`, `feedback_processor/main.py`

### Priority 2: User Experience

4. **Natural Language Task Creation**
   - **Current**: Multi-step conversation (source type → target)
   - **Improvement**: Single command parsing
   - **Example**: `/newtask monitor r/python for web framework posts`
   - **Files to modify**: `master_bot/main.py`, add NLP parsing

5. **Rich Notifications**
   - **Current**: Text-only messages
   - **Improvement**: Images, videos, embedded previews
   - **Files to modify**: `notifier/main.py`, `consumer/main.py`

6. **Task Scheduling**
   - **Feature**: Custom scraping frequencies per task
   - **Example**: Urgent news every 1 minute, general content every hour
   - **Database**: Add `scraping_interval` column to tasks

7. **Search History**
   - **Feature**: `/search <keyword>` to find past notifications
   - **Database**: New table `notification_history`

### Priority 3: Scalability

8. **Horizontal Scaling**
   - **Current**: Single instance of each service
   - **Improvement**: Multiple consumer/producer instances
   - **Files to modify**: `docker-compose.yml`, add `deploy: replicas: 3`

9. **Caching Layer**
   - **Feature**: Redis cache for hot database queries
   - **Benefit**: Reduce database load for frequently accessed tasks
   - **Implementation**: Add Redis service, modify `shared/database.py`

10. **Queue Prioritization**
    - **Feature**: Priority queues for urgent vs. regular content
    - **Benefit**: Time-sensitive notifications delivered faster
    - **Implementation**: Use RabbitMQ priority queues

### Priority 4: Advanced Features

11. **More Data Sources**
    - Twitter/X API
    - Hacker News API (native, not RSS)
    - YouTube channels
    - GitHub repositories (new releases, issues)
    - News APIs (NewsAPI, GDELT)

12. **Content Summarization**
    - **Feature**: LLM generates summaries of long articles
    - **Benefit**: Faster content consumption
    - **Implementation**: Add summarization step in consumer

13. **Multi-Criteria Filtering**
    - **Current**: Single prompt per task
    - **Improvement**: AND/OR/NOT logic with multiple conditions
    - **Example**: "Python AND (web OR framework) NOT Django"

14. **Sentiment Analysis**
    - **Feature**: Filter by sentiment (positive/negative/neutral)
    - **Use Case**: Only show positive product reviews

15. **Web Dashboard**
    - **Feature**: Web UI for task management (alternative to Telegram)
    - **Stack**: React frontend, FastAPI backend
    - **Files**: New `dashboard/` directory

16. **Analytics & Insights**
    - **Feature**: Statistics dashboard
      - Tasks created/deleted per day
      - Most active sources
      - Filtering accuracy
      - User engagement
    - **Implementation**: New `analytics/` service with visualization

17. **Collaborative Filtering**
    - **Feature**: "Users who liked X also liked Y" recommendations
    - **Benefit**: Suggest new sources to users
    - **Implementation**: Machine learning model, collaborative filtering

18. **Multi-Language Support**
    - **Feature**: Bot interface in multiple languages
    - **Implementation**: i18n library, language detection

### Priority 5: DevOps & Monitoring

19. **Health Checks**
    - **Current**: Basic Docker health checks
    - **Improvement**: Comprehensive /health endpoints
    - **Implementation**: Add health check routes to all services

20. **Structured Logging**
    - **Current**: Basic print-style logs
    - **Improvement**: JSON structured logs with ELK stack
    - **Benefit**: Better log analysis and alerting

21. **Metrics & Alerting**
    - **Tools**: Prometheus + Grafana
    - **Metrics**: Request latency, error rates, queue depths
    - **Alerts**: Email/Slack when errors exceed threshold

22. **Automated Testing**
    - **Unit Tests**: pytest for all modules
    - **Integration Tests**: Test service interactions
    - **E2E Tests**: Selenium for full user flows
    - **CI/CD**: GitHub Actions for automated testing

23. **Database Migrations**
    - **Tool**: Alembic for SQLAlchemy
    - **Benefit**: Safe schema updates without downtime

24. **Configuration Management**
    - **Current**: .env file
    - **Improvement**: Consul/Vault for secrets management
    - **Benefit**: Centralized config, automatic rotation

### Priority 6: Security

25. **User Authentication**
    - **Current**: Any Telegram user can use bot
    - **Improvement**: Whitelist/invite system
    - **Implementation**: User registration table

26. **Rate Limiting Per User**
    - **Feature**: Prevent abuse (max 10 tasks per user)
    - **Implementation**: Add task count validation

27. **Input Sanitization**
    - **Issue**: User input not fully validated
    - **Risk**: SQL injection, XSS (low risk with current stack)
    - **Solution**: Comprehensive input validation

28. **Secrets Rotation**
    - **Feature**: Automatic rotation of API keys
    - **Benefit**: Improved security posture

---

## Testing Checklist

Before deploying to production:

- [ ] All manual test cases pass
- [ ] Services restart successfully after crash
- [ ] Data persists after `docker-compose down` (volumes work)
- [ ] Notifications arrive within 5 minutes of new content
- [ ] Feedback updates prompts correctly
- [ ] Multiple users can use bot simultaneously
- [ ] Resource usage is acceptable (<2GB RAM, <20% CPU)
- [ ] Logs show no recurring errors
- [ ] RabbitMQ queues don't grow unbounded
- [ ] Database backup strategy implemented
- [ ] Documentation is up to date

---

## Contributing Test Cases

When adding new features, please:

1. Add corresponding test case to this document
2. Include expected results and verification steps
3. Document any new dependencies or setup requirements
4. Update the troubleshooting section with common issues

---

## Support

For testing issues:
1. Check logs: `docker-compose logs -f [service_name]`
2. Verify .env configuration
3. Consult troubleshooting section above
4. Open GitHub issue with:
   - Test case that failed
   - Error logs
   - Environment details (OS, Docker version)

---

**Last Updated**: 2025-10-06
**Document Version**: 1.0
**Veritas Version**: 1.0
