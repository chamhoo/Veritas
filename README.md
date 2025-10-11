# Veritas - Dynamic Interactive Information Pipeline using Email

Veritas is an intelligent agent that monitors information sources and sends you relevant updates via email. You control everything through simple email commands, and the system learns from your feedback to get better over time.

## Features

- **Email-based Interface**: Control the system entirely via email commands
- **Automated Monitoring**: Set up continuous monitoring of Reddit or RSS sources
- **Intelligent Filtering**: AI-powered content filtering using OpenRouter (compatible with OpenAI)
- **Interactive Refinement**: System learns from your feedback to improve results
- **Task Management**: Create, list, pause, resume, and delete tasks through email

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Email account with IMAP and SMTP access
- OpenRouter API key

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/veritas.git
   cd veritas
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file and fill in your:
   - Database credentials
   - RabbitMQ settings (defaults should work)
   - OpenRouter API key
   - IMAP settings for receiving emails
   - SMTP settings for sending emails

3. **Start the services:**
   ```bash
   docker-compose up -d
   ```

4. **Send your first command email:**
   
   Send an email to the email address you configured with:
   - Subject: `New Task`
   - Body: `monitor the r/python subreddit for news about web frameworks`

   The system will confirm task creation and start monitoring.

## Email Commands

Send emails with these subject lines to control the system:

- **Create a new monitoring task**
  - Subject: `New Task`
  - Body: Your monitoring request (e.g., "monitor r/programming for news about Rust")

- **List your current tasks**
  - Subject: `List Tasks`

- **Pause a task**
  - Subject: `Pause Task`
  - Body: Task ID (e.g., "123")

- **Resume a paused task**
  - Subject: `Resume Task`
  - Body: Task ID (e.g., "123")

- **Delete a task**
  - Subject: `Delete Task`
  - Body: Task ID (e.g., "123")

## Providing Feedback

When you receive a notification email, simply reply to it with your feedback:
- If the content wasn't relevant, explain why.
- If you want more content like this, mention which aspects you liked.
- The system will use your feedback to improve future filtering.

## Architecture

Veritas uses a microservice architecture with the following components:

- **Mail Gateway**: Processes incoming emails and commands
- **Producer**: Scrapes content from sources
- **Consumer**: Filters content using LLM
- **Notifier**: Sends email notifications
- **Feedback Processor**: Improves filtering based on feedback

Data flows through RabbitMQ message queues, and PostgreSQL stores task information.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
