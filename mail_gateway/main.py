"""
Mail Gateway Service

Polls IMAP inbox for command emails and processes user feedback.
"""
import os
import sys
import time
import json
import re
import email
from email.header import decode_header
from datetime import datetime
from imaplib import IMAP4_SSL
from typing import Optional, Dict, Any

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, init_db
from shared.models import Task
from shared.mq_utils import publish_message


class MailGateway:
    def __init__(self):
        self.imap_server = os.getenv("IMAP_SERVER")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "60"))

    def connect_imap(self):
        """Connect to IMAP server."""
        try:
            mail = IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            return mail
        except Exception as e:
            print(f"Failed to connect to IMAP: {e}")
            raise

    def decode_header_value(self, value):
        """Decode email header value."""
        if value is None:
            return ""
        decoded = decode_header(value)
        result = ""
        for part, encoding in decoded:
            if isinstance(part, bytes):
                result += part.decode(encoding or "utf-8", errors="ignore")
            else:
                result += part
        return result

    def extract_task_id_from_body(self, body: str) -> Optional[int]:
        """Extract task ID from notification email body."""
        match = re.search(r"Task ID:\s*(\d+)", body)
        if match:
            return int(match.group(1))
        return None

    def parse_source_info(self, description: str) -> Dict[str, Any]:
        """
        Parse user description to extract source type and parameters.

        Examples:
        - "monitor /r/python subreddit for news about web frameworks"
        - "watch RSS feed https://example.com/feed.xml for AI news"
        """
        description_lower = description.lower()

        # Reddit detection
        reddit_match = re.search(r'/r/(\w+)|subreddit\s+(\w+)|reddit.*?(\w+)', description_lower)
        if reddit_match or "reddit" in description_lower or "/r/" in description_lower:
            # Extract subreddit name
            subreddit = None
            if reddit_match:
                subreddit = reddit_match.group(1) or reddit_match.group(2) or reddit_match.group(3)

            if not subreddit:
                # Default to 'python' if mentioned
                subreddit = "python" if "python" in description_lower else "all"

            return {
                "source_type": "reddit",
                "source_params": json.dumps({
                    "subreddit": subreddit,
                    "limit": 25
                })
            }

        # RSS detection
        rss_match = re.search(r'https?://[^\s]+', description)
        if rss_match or "rss" in description_lower or "feed" in description_lower:
            url = rss_match.group(0) if rss_match else ""
            return {
                "source_type": "rss",
                "source_params": json.dumps({
                    "url": url
                })
            }

        # Default to Reddit if unclear
        return {
            "source_type": "reddit",
            "source_params": json.dumps({
                "subreddit": "all",
                "limit": 25
            })
        }

    def generate_initial_prompt(self, description: str) -> str:
        """
        Generate initial LLM filtering prompt based on user's request.
        """
        return f"""You are a content filter. Your task is to determine if content is relevant to the user's criteria.

User's criteria: {description}

Analyze the following content and respond with ONLY "YES" if it matches the criteria, or "NO" if it doesn't.
Be strict but fair in your judgment. Consider the topic, keywords, and intent.

Content to analyze:
{{{{CONTENT}}}}

Your decision (YES or NO):"""

    def handle_new_task(self, user_email: str, description: str):
        """Create a new monitoring task."""
        try:
            # Parse source information
            source_info = self.parse_source_info(description)

            # Generate initial prompt
            initial_prompt = self.generate_initial_prompt(description)

            with get_db() as db:
                task = Task(
                    user_email=user_email,
                    command="New Task",
                    description=description,
                    source_type=source_info["source_type"],
                    source_params=source_info["source_params"],
                    current_prompt=initial_prompt,
                    status="active"
                )
                db.add(task)
                db.flush()

                print(f"Created task {task.id} for {user_email}: {description[:50]}...")

                # Send confirmation email via notifier
                publish_message("filtered_content_queue", {
                    "task_id": task.id,
                    "user_email": user_email,
                    "subject": f"Task Created - #{task.id}",
                    "body": f"""Your monitoring task has been created successfully.

Task ID: {task.id}
Description: {description}
Source: {source_info["source_type"]}
Status: Active

You will receive email notifications when relevant content is found.
Reply to any notification with feedback like "this is relevant" or "this is not what I want" to help improve filtering.

To manage your tasks:
- List Tasks: See all your tasks
- Pause Task {task.id}: Temporarily stop this task
- Delete Task {task.id}: Remove this task permanently
"""
                })

        except Exception as e:
            print(f"Error creating task: {e}")

    def handle_list_tasks(self, user_email: str):
        """List all tasks for a user."""
        try:
            with get_db() as db:
                tasks = db.query(Task).filter(
                    Task.user_email == user_email,
                    Task.status != "deleted"
                ).all()

                if not tasks:
                    body = "You have no active tasks."
                else:
                    body = "Your tasks:\n\n"
                    for task in tasks:
                        body += f"Task ID: {task.id}\n"
                        body += f"Status: {task.status}\n"
                        body += f"Description: {task.description}\n"
                        body += f"Created: {task.created_at}\n"
                        body += "-" * 50 + "\n\n"

                # Send via notifier
                publish_message("filtered_content_queue", {
                    "task_id": None,
                    "user_email": user_email,
                    "subject": "Your Tasks",
                    "body": body
                })

        except Exception as e:
            print(f"Error listing tasks: {e}")

    def handle_pause_task(self, user_email: str, task_id: int):
        """Pause a specific task."""
        try:
            with get_db() as db:
                task = db.query(Task).filter(
                    Task.id == task_id,
                    Task.user_email == user_email
                ).first()

                if task:
                    task.status = "paused"
                    db.flush()

                    publish_message("filtered_content_queue", {
                        "task_id": task_id,
                        "user_email": user_email,
                        "subject": f"Task #{task_id} Paused",
                        "body": f"Task #{task_id} has been paused. Send 'Resume Task {task_id}' to reactivate it."
                    })
                else:
                    publish_message("filtered_content_queue", {
                        "task_id": None,
                        "user_email": user_email,
                        "subject": "Task Not Found",
                        "body": f"Task #{task_id} not found or doesn't belong to you."
                    })

        except Exception as e:
            print(f"Error pausing task: {e}")

    def handle_resume_task(self, user_email: str, task_id: int):
        """Resume a paused task."""
        try:
            with get_db() as db:
                task = db.query(Task).filter(
                    Task.id == task_id,
                    Task.user_email == user_email
                ).first()

                if task:
                    task.status = "active"
                    db.flush()

                    publish_message("filtered_content_queue", {
                        "task_id": task_id,
                        "user_email": user_email,
                        "subject": f"Task #{task_id} Resumed",
                        "body": f"Task #{task_id} is now active again."
                    })

        except Exception as e:
            print(f"Error resuming task: {e}")

    def handle_delete_task(self, user_email: str, task_id: int):
        """Delete a specific task."""
        try:
            with get_db() as db:
                task = db.query(Task).filter(
                    Task.id == task_id,
                    Task.user_email == user_email
                ).first()

                if task:
                    task.status = "deleted"
                    db.flush()

                    publish_message("filtered_content_queue", {
                        "task_id": task_id,
                        "user_email": user_email,
                        "subject": f"Task #{task_id} Deleted",
                        "body": f"Task #{task_id} has been deleted."
                    })

        except Exception as e:
            print(f"Error deleting task: {e}")

    def handle_feedback(self, user_email: str, task_id: int, feedback: str):
        """Process user feedback for a task."""
        try:
            with get_db() as db:
                task = db.query(Task).filter(
                    Task.id == task_id,
                    Task.user_email == user_email
                ).first()

                if task:
                    # Publish to feedback queue
                    publish_message("feedback_queue", {
                        "task_id": task_id,
                        "feedback": feedback,
                        "current_prompt": task.current_prompt
                    })

                    print(f"Received feedback for task {task_id}: {feedback[:50]}...")

        except Exception as e:
            print(f"Error handling feedback: {e}")

    def process_email(self, msg_data):
        """Process a single email message."""
        try:
            msg = email.message_from_bytes(msg_data)

            # Extract headers
            from_header = self.decode_header_value(msg.get("From", ""))
            subject = self.decode_header_value(msg.get("Subject", "")).strip()

            # Extract sender email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_header)
            sender_email = email_match.group(0) if email_match else ""

            if not sender_email:
                print("Could not extract sender email, skipping...")
                return

            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")
                        break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")

            body = body.strip()

            print(f"Processing email from {sender_email}: {subject}")

            # Check if it's a reply (has In-Reply-To or References)
            in_reply_to = msg.get("In-Reply-To")
            references = msg.get("References")

            # Try to extract task ID from body for feedback
            task_id_from_body = self.extract_task_id_from_body(body)

            if (in_reply_to or references) and task_id_from_body:
                # This is feedback
                self.handle_feedback(sender_email, task_id_from_body, body)
                return

            # Parse command from subject
            subject_lower = subject.lower()

            if subject_lower == "new task" or subject_lower.startswith("new task"):
                self.handle_new_task(sender_email, body)

            elif subject_lower == "list tasks" or subject_lower.startswith("list task"):
                self.handle_list_tasks(sender_email)

            elif subject_lower.startswith("pause task"):
                # Extract task ID
                match = re.search(r'pause task\s+(\d+)', subject_lower)
                if match:
                    task_id = int(match.group(1))
                    self.handle_pause_task(sender_email, task_id)

            elif subject_lower.startswith("resume task"):
                # Extract task ID
                match = re.search(r'resume task\s+(\d+)', subject_lower)
                if match:
                    task_id = int(match.group(1))
                    self.handle_resume_task(sender_email, task_id)

            elif subject_lower.startswith("delete task"):
                # Extract task ID
                match = re.search(r'delete task\s+(\d+)', subject_lower)
                if match:
                    task_id = int(match.group(1))
                    self.handle_delete_task(sender_email, task_id)

            else:
                print(f"Unknown command: {subject}")

        except Exception as e:
            print(f"Error processing email: {e}")

    def poll(self):
        """Main polling loop."""
        print(f"Mail Gateway started. Polling every {self.poll_interval} seconds...")

        while True:
            try:
                mail = self.connect_imap()
                mail.select("INBOX")

                # Search for unread emails
                status, messages = mail.search(None, "UNSEEN")

                if status == "OK":
                    email_ids = messages[0].split()

                    for email_id in email_ids:
                        try:
                            # Fetch email
                            status, msg_data = mail.fetch(email_id, "(RFC822)")

                            if status == "OK":
                                self.process_email(msg_data[0][1])

                                # Mark as read
                                mail.store(email_id, "+FLAGS", "\\Seen")
                        except Exception as e:
                            print(f"Error processing email {email_id}: {e}")

                mail.close()
                mail.logout()

            except Exception as e:
                print(f"Error in polling loop: {e}")

            time.sleep(self.poll_interval)


def main():
    # Initialize database
    print("Initializing database...")
    init_db()

    # Start mail gateway
    gateway = MailGateway()
    gateway.poll()


if __name__ == "__main__":
    main()
