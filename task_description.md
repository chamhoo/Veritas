You are an expert-level software architect and Python developer. Your mission is to design and build a complete, runnable codebase for a Dynamic Interactive Information Pipeline using Email.

1. Core Vision & Functional Requirements
The system you will build is an intelligent agent that users can command via email. The core user journey is as follows:

Task Creation: A user sends an email to a designated system address. The subject line acts as the command, and the body contains the details. For example:
To: agent@yourdomain.com
Subject: New Task
Body: monitor the /r/python subreddit for news about web frameworks
Automated Monitoring: The system automatically creates a background task to continuously watch the specified source.
Intelligent Filtering: When new content appears, the system utilises the LLM-based agent API provided by OpenRouter to determine if it aligns with the user's specific criteria.
Notification: If the content is relevant, it's sent to the user as a new email.
Interactive Refinement: The user can provide feedback by replying to a notification email. For example, replying with "this is irrelevant" or "show me more like this". The system then uses this feedback to automatically refine and improve its filtering criteria for that specific task.
Task Management: Users must also have simple email commands to list, pause, and delete their monitoring tasks (e.g., by sending an email with the subject List Tasks or Pause Task 123).
2. Architectural Blueprint & Key Technologies
To achieve this, you will implement an event-driven, microservice-style architecture. This ensures scalability and robustness.

Core Technologies:
Language: Python
Orchestration: Docker
Messaging: RabbitMQ for asynchronous communication between services.
Database: PostgreSQL for persistent task storage.
LLM Provider: OpenRouter API (OpenAI-compatible endpoint).
Service Components:
Mail Gateway: The user's main interface. It polls an IMAP inbox for command emails and parses replies for feedback.
Producer: Manages and runs the data scrapers.
Consumer: The core filtering engine that communicates with OpenRouter.
Notifier: Delivers results to the user via SMTP.
Feedback Processor: The "learning" component that refines prompts.
4. Component Responsibilities
Here is what each service recommends to accomplish. Refine and implement them using best practices in Python.

Mail Gateway:
Act as the primary interface by polling a dedicated IMAP inbox at regular intervals.
Parse incoming emails to identify commands (from the subject) and parameters (from the body).
Translate commands (New Task, List Tasks, etc.) into database operations (CREATE, READ, UPDATE).
When a New Task command is received, intelligently generate an initial current_prompt for the LLM based on the user's request in the email body.
Parse replies to notification emails to capture user feedback. Use email headers (In-Reply-To, References) and embedded identifiers to link feedback to the correct task.
Publish captured feedback to the feedback_queue.
Producer:
Periodically check the database for all active tasks.
For each task, run the appropriate scraper (e.g., for Reddit, RSS).
To prevent duplicates, keep track of which items have already been processed for each task.
Place any new, unprocessed items onto the raw_content_queue.
Consumer (Filter):
Listen for new content on the raw_content_queue.
For each piece of content, retrieve the corresponding task's current_prompt from the database.
Make a call to the OpenRouter API, sending both the prompt and the content, to get a "YES" or "NO" style decision.
If the decision is "YES", format a user-friendly email subject and body, and place it on the filtered_content_queue.
Notifier:
Listen for messages on the filtered_content_queue.
Send the message to the correct user_email using an SMTP server.
Ensure each notification email includes a unique identifier (like Task ID: 123) in the body and clear instructions on how the user can reply to provide feedback. This is crucial for the Mail Gateway to process feedback correctly.
Feedback Processor:
Listen for events on the feedback_queue.
For each feedback event, use another LLM-based agent. Your goal is to generate a new, improved current_prompt based on the original prompt and user feedback.
Update the task's current_prompt in the database with the newly generated version.
5. Final Deliverables
Please provide the following:

Codebase and Configuration:

The complete, runnable Python codebase for all services.
A docker-compose.yml file that defines and orchestrates the entire application stack (all Python services, plus PostgreSQL and RabbitMQ).
A README.md file that clearly explains the project's purpose, environment variables, and setup instructions.
An .env.example file to serve as a template for environment variables.
Structure Recommand:

dynamic-info-pipeline/ ├── .env.example ├── docker-compose.yml ├── README.md ├── mail_gateway/ │ ├── Dockerfile │ ├── main.py │ └── requirements.txt ├── producer/ │ ├── Dockerfile │ ├── main.py │ ├── scrapers/ │ │ ├── __init__.py │ │ ├── reddit_scraper.py │ │ └── rss_scraper.py │ └── requirements.txt ├── consumer/ │ ├── Dockerfile │ ├── main.py │ └── requirements.txt ├── notifier/ │ ├── Dockerfile │ ├── main.py │ └── requirements.txt ├── feedback_processor/ │ ├── Dockerfile │ ├── main.py │ └── requirements.txt └── shared/ ├── database.py # SQLAlchemy engine, session setup, base model ├── models.py # The 'tasks' table model definition └── mq_utils.py # Utility functions for RabbitMQ connection/publishing

Documentation: The README.md file must provide clear, step-by-step instructions to get the entire system running