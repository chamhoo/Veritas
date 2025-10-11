You are an expert-level software architect and Python developer. Your mission is to design and build a complete, runnable codebase for a **Dynamic Interactive Information Pipeline using Email**.

### 1. Core Vision & Functional Requirements

The system you will build is an intelligent agent that users can command via **email**. The core user journey is as follows:

1. **Task Creation**: A user sends an email to a designated system address. The **subject line** acts as the command, and the **body** contains the details. For example:
    - **To**: `agent@yourdomain.com`
    - **Subject**: `New Task`
    - **Body**: `monitor the /r/python subreddit for news about web frameworks`
2. **Automated Monitoring**: The system automatically creates a background task to continuously watch the specified source.
3. **Intelligent Filtering**: When new content appears, the system uses the OpenRouter LLM API to decide if it matches the user's specific criteria.
4. **Notification**: If the content is relevant, it's sent to the user as a **new email**.
5. **Interactive Refinement**: The user can provide feedback by **replying** to a notification email. For example, replying with "this is irrelevant" or "show me more like this". The system then uses this feedback to automatically refine and improve its filtering criteria for that specific task.
6. **Task Management**: Users must also have simple email commands to list, pause, and delete their monitoring tasks (e.g., by sending an email with the subject `List Tasks` or `Pause Task 123`).

### 2. Architectural Blueprint & Key Technologies

To achieve this, you will implement an event-driven, microservice-style architecture. This ensures scalability and robustness.

- **Core Technologies**:
    - **Language**: Python 3.10+
    - **Orchestration**: Docker and Docker Compose
    - **Messaging**: RabbitMQ for asynchronous communication between services.
    - **Database**: PostgreSQL for persistent task storage. Use a standard ORM like SQLAlchemy.
    - **LLM Provider**: OpenRouter API (OpenAI-compatible endpoint).
    - **Email Handling**: Python's built-in `imaplib` (for receiving) and `smtplib` (for sending).
- **Service Components**:
    - **Mail Gateway**: The user's main interface. It polls an IMAP inbox for command emails and parses replies for feedback.
    - **Producer**: Manages and runs the data scrapers.
    - **Consumer**: The core filtering engine that communicates with OpenRouter.
    - **Notifier**: Delivers results to the user via SMTP.
    - **Feedback Processor**: The "learning" component that refines prompts.

---

### 3. System Contracts (The Non-Negotiables)

For the system to function correctly, all services must adhere to the following data contracts.

### 3.1. Database Schema (`tasks` table)

This is the single source of truth for all monitoring tasks.

| Column | Type | Description |
| --- | --- | --- |
| `task_id` | `SERIAL PRIMARY KEY` | Unique identifier for the task. |
| `user_email` | `VARCHAR(255)` | The user's email address. Used for both identification and notifications. |
| `source_type` | `VARCHAR(50)` | e.g., 'reddit', 'rss'. |
| `source_target` | `TEXT` | e.g., 'r/python' or a feed URL. |
| `current_prompt` | `TEXT` | The LLM prompt used for filtering. This will be updated by the feedback loop. |
| `status` | `VARCHAR(50)` | 'active' or 'paused'. |

### 3.2. Message Queue Payloads (JSON format)

- **`raw_content_queue`** (from Producer to Consumer):JSON
    
    # 
    
    `{
      "task_id": 123,
      "data": {
        "title": "...", "url": "...", "content": "..."
      }
    }`
    
- **`filtered_content_queue`** (from Consumer to Notifier):JSON
    
    # 
    
    `{
      "user_email": "user@example.com",
      "formatted_subject": "New Update on Your Task: ...",
      "formatted_body": "...",
      "task_id_for_feedback": 123
    }`
    
- **`feedback_queue`** (from Mail Gateway to Feedback Processor):JSON
    
    # 
    
    `{
      "task_id": 123,
      "feedback_text": "...",
      "current_prompt": "..."
    }`
    

---

### 4. Component Responsibilities

Here is what each service needs to accomplish. Implement them using Python best practices.

- **Mail Gateway**:
    - Act as the primary interface by polling a dedicated IMAP inbox at regular intervals.
    - Parse incoming emails to identify commands (from the subject) and parameters (from the body).
    - Translate commands (`New Task`, `List Tasks`, etc.) into database operations (CREATE, READ, UPDATE).
    - When a `New Task` command is received, intelligently generate an initial `current_prompt` for the LLM based on the user's request in the email body.
    - Parse **replies** to notification emails to capture user feedback. Use email headers (`In-Reply-To`, `References`) and embedded identifiers to link feedback to the correct task.
    - Publish captured feedback to the `feedback_queue`.
- **Producer**:
    - Periodically check the database for all `active` tasks.
    - For each task, run the appropriate scraper (e.g., for Reddit, RSS).
    - To prevent duplicates, keep track of which items have already been processed for each task.
    - Place any new, unprocessed items onto the `raw_content_queue`.
- **Consumer (Filter)**:
    - Listen for new content on the `raw_content_queue`.
    - For each piece of content, retrieve the corresponding task's `current_prompt` from the database.
    - Make a call to the OpenRouter API, sending both the prompt and the content, to get a "YES" or "NO" style decision.
    - If the decision is "YES", format a user-friendly email subject and body, and place it on the `filtered_content_queue`.
- **Notifier**:
    - Listen for messages on the `filtered_content_queue`.
    - Send the message to the correct `user_email` using an SMTP server.
    - Ensure each notification email includes a unique identifier (like `Task ID: 123`) in the body and clear instructions on how the user can **reply** to provide feedback. This is crucial for the Mail Gateway to process feedback correctly.
- **Feedback Processor**:
    - Listen for events on the `feedback_queue`.
    - For each feedback event, use the OpenRouter API in a "meta" capacity. Your goal is to generate a new, improved `current_prompt` based on the old prompt and the user's feedback.
    - Update the task's `current_prompt` in the database with the newly generated version.

---

### 5. Final Deliverables

Please provide the following:

1. **Codebase and Configuration**:
    - The complete, runnable Python codebase for all services.
    - A `docker-compose.yml` file that defines and orchestrates the entire application stack (all Python services, plus PostgreSQL and RabbitMQ).
    - A `README.md` file that clearly explains the project's purpose, environment variables, and setup instructions.
    - An `.env.example` file to serve as a template for environment variables.
2. **Required Directory Structure**: The entire project must be organized using the following structure to ensure clarity and maintainability.
    
    `veritas/
    ├── .env.example
    ├── docker-compose.yml
    ├── README.md
    ├── mail_gateway/
    │   ├── Dockerfile
    │   ├── main.py
    │   └── requirements.txt
    ├── producer/
    │   ├── Dockerfile
    │   ├── main.py
    │   ├── scrapers/
    │   │   ├── __init__.py
    │   │   ├── reddit_scraper.py
    │   │   └── rss_scraper.py
    │   └── requirements.txt
    ├── consumer/
    │   ├── Dockerfile
    │   ├── main.py
    │   └── requirements.txt
    ├── notifier/
    │   ├── Dockerfile
    │   ├── main.py
    │   └── requirements.txt
    ├── feedback_processor/
    │   ├── Dockerfile
    │   ├── main.py
    │   └── requirements.txt
    └── shared/
        ├── database.py       # SQLAlchemy engine, session setup, base model
        ├── models.py         # The 'tasks' table model definition
        └── mq_utils.py       # Utility functions for RabbitMQ connection/publishing`
    
3. **Documentation**: The `README.md` file must provide clear, step-by-step instructions to get the entire system running with a single `docker-compose up` command, after setting up the `.env` file with the necessary credentials:
    - `DATABASE_URL`
    - `RABBITMQ_URL`
    - `OPENROUTER_API_KEY`
    - **IMAP settings**: `IMAP_SERVER`, `IMAP_USERNAME`, `IMAP_PASSWORD`
    - **SMTP settings**: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`