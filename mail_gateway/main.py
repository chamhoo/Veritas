import os
import sys
import time
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import re
import json

# Add shared module to path
sys.path.insert(0, '/root/Veritas')

from dotenv import load_dotenv
from openai import OpenAI

from shared.database import get_session, init_db
from shared.models import Task, TaskStatus, SourceType
from shared.mq_utils import publish_message, FEEDBACK_QUEUE

load_dotenv()

# OpenRouter client
client = OpenAI(
    base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
    api_key=os.getenv('OPENROUTER_API_KEY')
)

def get_imap_connection():
    """Connect to IMAP server."""
    host = os.getenv('IMAP_HOST')
    port = int(os.getenv('IMAP_PORT', '993'))
    user = os.getenv('IMAP_USER')
    password = os.getenv('IMAP_PASSWORD')

    mail = imaplib.IMAP4_SSL(host, port)
    mail.login(user, password)
    return mail

def decode_email_subject(subject):
    """Decode email subject handling various encodings."""
    if subject is None:
        return ""

    decoded_parts = decode_header(subject)
    decoded_subject = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
        else:
            decoded_subject += part

    return decoded_subject.strip()

def get_email_body(msg):
    """Extract plain text body from email message."""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = ""

    return body.strip()

def parse_source_from_request(request_text):
    """
    Parse the source type and identifier from user request.
    Returns (source_type, source_identifier) or (None, None) if not found.
    """
    request_lower = request_text.lower()

    # Check for Reddit
    reddit_patterns = [
        r'/r/(\w+)',
        r'r/(\w+)',
        r'subreddit\s+(\w+)',
        r'reddit.*?(\w+)\s+subreddit'
    ]

    for pattern in reddit_patterns:
        match = re.search(pattern, request_text, re.IGNORECASE)
        if match:
            return SourceType.REDDIT, match.group(1)

    # Check for RSS
    rss_patterns = [
        r'(https?://[^\s]+\.rss)',
        r'(https?://[^\s]+/rss)',
        r'(https?://[^\s]+/feed[^\s]*)',
        r'rss[:\s]+(https?://[^\s]+)'
    ]

    for pattern in rss_patterns:
        match = re.search(pattern, request_text, re.IGNORECASE)
        if match:
            return SourceType.RSS, match.group(1)

    # Default to Reddit if "reddit" mentioned without specific subreddit
    if 'reddit' in request_lower:
        # Try to extract any word that might be a subreddit name
        words = re.findall(r'\b\w+\b', request_text)
        for word in words:
            if word.lower() not in ['reddit', 'subreddit', 'monitor', 'watch', 'the', 'for', 'about', 'news']:
                return SourceType.REDDIT, word

    return None, None

def generate_initial_prompt(request_text):
    """Use LLM to generate an initial filtering prompt based on user request."""
    try:
        response = client.chat.completions.create(
            model=os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
            messages=[
                {
                    "role": "system",
                    "content": """You are a prompt engineer. Given a user's monitoring request,
                    create a clear and specific prompt that will be used to filter content.
                    The prompt should help an LLM decide if a piece of content is relevant to the user's interests.

                    Output ONLY the prompt text, nothing else. The prompt should:
                    1. Clearly state what topics/themes to look for
                    2. Specify what makes content relevant
                    3. Be specific enough to avoid false positives

                    Example output:
                    "Determine if this content is relevant to Python web frameworks.
                    Look for: discussions about Flask, Django, FastAPI, or similar frameworks;
                    announcements of new features or releases; tutorials or best practices;
                    performance comparisons. Ignore: general Python questions unrelated to web development."
                    """
                },
                {
                    "role": "user",
                    "content": f"User request: {request_text}"
                }
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating prompt: {e}")
        # Fallback to a basic prompt
        return f"Determine if this content is relevant to: {request_text}. Answer YES if relevant, NO if not."

def handle_new_task(sender_email, body):
    """Create a new monitoring task."""
    session = get_session()
    try:
        source_type, source_id = parse_source_from_request(body)

        if not source_type or not source_id:
            return f"Could not parse source from your request. Please specify a source like '/r/python' for Reddit or an RSS URL."

        # Generate initial prompt using LLM
        initial_prompt = generate_initial_prompt(body)

        task = Task(
            user_email=sender_email,
            source_type=source_type,
            source_identifier=source_id,
            original_request=body,
            current_prompt=initial_prompt,
            status=TaskStatus.ACTIVE
        )

        session.add(task)
        session.commit()

        return f"Task created successfully!\n\nTask ID: {task.id}\nSource: {source_type.value}:{source_id}\nStatus: Active\n\nI will monitor this source and notify you when I find relevant content."

    except Exception as e:
        session.rollback()
        return f"Error creating task: {str(e)}"
    finally:
        session.close()

def handle_list_tasks(sender_email):
    """List all tasks for a user."""
    session = get_session()
    try:
        tasks = session.query(Task).filter(
            Task.user_email == sender_email,
            Task.status != TaskStatus.DELETED
        ).all()

        if not tasks:
            return "You have no active tasks."

        response = "Your tasks:\n\n"
        for task in tasks:
            response += f"Task ID: {task.id}\n"
            response += f"  Source: {task.source_type.value}:{task.source_identifier}\n"
            response += f"  Status: {task.status.value}\n"
            response += f"  Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"

        return response

    finally:
        session.close()

def handle_pause_task(sender_email, body):
    """Pause a specific task."""
    session = get_session()
    try:
        # Extract task ID from body
        match = re.search(r'\b(\d+)\b', body)
        if not match:
            return "Please specify a task ID to pause (e.g., 'Pause task 123')"

        task_id = int(match.group(1))

        task = session.query(Task).filter(
            Task.id == task_id,
            Task.user_email == sender_email
        ).first()

        if not task:
            return f"Task {task_id} not found or you don't have permission to modify it."

        if task.status == TaskStatus.PAUSED:
            return f"Task {task_id} is already paused."

        task.status = TaskStatus.PAUSED
        session.commit()

        return f"Task {task_id} has been paused. Send 'Resume Task {task_id}' to reactivate it."

    except Exception as e:
        session.rollback()
        return f"Error pausing task: {str(e)}"
    finally:
        session.close()

def handle_resume_task(sender_email, body):
    """Resume a paused task."""
    session = get_session()
    try:
        match = re.search(r'\b(\d+)\b', body)
        if not match:
            return "Please specify a task ID to resume (e.g., 'Resume task 123')"

        task_id = int(match.group(1))

        task = session.query(Task).filter(
            Task.id == task_id,
            Task.user_email == sender_email
        ).first()

        if not task:
            return f"Task {task_id} not found or you don't have permission to modify it."

        if task.status == TaskStatus.ACTIVE:
            return f"Task {task_id} is already active."

        task.status = TaskStatus.ACTIVE
        session.commit()

        return f"Task {task_id} has been resumed and is now active."

    except Exception as e:
        session.rollback()
        return f"Error resuming task: {str(e)}"
    finally:
        session.close()

def handle_delete_task(sender_email, body):
    """Delete a specific task."""
    session = get_session()
    try:
        match = re.search(r'\b(\d+)\b', body)
        if not match:
            return "Please specify a task ID to delete (e.g., 'Delete task 123')"

        task_id = int(match.group(1))

        task = session.query(Task).filter(
            Task.id == task_id,
            Task.user_email == sender_email
        ).first()

        if not task:
            return f"Task {task_id} not found or you don't have permission to delete it."

        task.status = TaskStatus.DELETED
        session.commit()

        return f"Task {task_id} has been deleted."

    except Exception as e:
        session.rollback()
        return f"Error deleting task: {str(e)}"
    finally:
        session.close()

def handle_feedback(sender_email, body, in_reply_to, references):
    """Process user feedback from a reply email."""
    # Try to extract task ID from email body or references
    task_id = None

    # Look for task ID in the original email thread
    combined_text = f"{body} {in_reply_to or ''} {references or ''}"
    match = re.search(r'Task\s*ID[:\s]*(\d+)', combined_text, re.IGNORECASE)

    if match:
        task_id = int(match.group(1))
    else:
        # Try to find any number that might be a task ID
        match = re.search(r'\b(\d+)\b', combined_text)
        if match:
            task_id = int(match.group(1))

    if not task_id:
        return "Could not identify which task this feedback is for. Please include the Task ID in your reply."

    # Verify task belongs to user
    session = get_session()
    try:
        task = session.query(Task).filter(
            Task.id == task_id,
            Task.user_email == sender_email
        ).first()

        if not task:
            return f"Task {task_id} not found or you don't have permission to modify it."

        # Publish feedback to queue for processing
        feedback_message = {
            'task_id': task_id,
            'user_email': sender_email,
            'feedback': body,
            'current_prompt': task.current_prompt
        }

        publish_message(FEEDBACK_QUEUE, feedback_message)

        return f"Feedback received for Task {task_id}. I will adjust my filtering criteria based on your input."

    finally:
        session.close()

def send_response_email(to_email, subject, body):
    """Send a response email to the user."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = f"Re: {subject}"

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Port 465 uses SSL, port 587 uses STARTTLS
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        print(f"Response sent to {to_email}")
    except Exception as e:
        print(f"Error sending response: {e}")

def process_email(msg):
    """Process a single email and return the appropriate response."""
    subject = decode_email_subject(msg.get('Subject', ''))
    sender = parseaddr(msg.get('From', ''))[1]
    body = get_email_body(msg)
    in_reply_to = msg.get('In-Reply-To', '')
    references = msg.get('References', '')

    print(f"Processing email from {sender}: {subject}")

    subject_lower = subject.lower().strip()

    # Determine command type
    if subject_lower == 'new task' or subject_lower.startswith('new task'):
        response = handle_new_task(sender, body)
    elif subject_lower == 'list tasks' or subject_lower.startswith('list'):
        response = handle_list_tasks(sender)
    elif subject_lower.startswith('pause'):
        response = handle_pause_task(sender, body if body else subject)
    elif subject_lower.startswith('resume'):
        response = handle_resume_task(sender, body if body else subject)
    elif subject_lower.startswith('delete'):
        response = handle_delete_task(sender, body if body else subject)
    elif in_reply_to or references or 'task id' in body.lower():
        # This is likely a feedback reply
        response = handle_feedback(sender, body, in_reply_to, references)
    else:
        response = """Unknown command. Available commands:

- Subject: 'New Task' - Create a new monitoring task (details in body)
- Subject: 'List Tasks' - List all your tasks
- Subject: 'Pause Task' - Pause a task (include task ID in body)
- Subject: 'Resume Task' - Resume a paused task
- Subject: 'Delete Task' - Delete a task

To provide feedback, simply reply to a notification email."""

    return sender, subject, response

def poll_inbox():
    """Poll the IMAP inbox for new emails."""
    try:
        mail = get_imap_connection()
        mail.select('INBOX')

        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')

        if status != 'OK':
            print("Error searching inbox")
            return

        email_ids = messages[0].split()

        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                sender, subject, response = process_email(msg)

                # Send response
                send_response_email(sender, subject, response)

                # Mark as read (already done by fetch, but let's be explicit)
                mail.store(email_id, '+FLAGS', '\\Seen')

            except Exception as e:
                print(f"Error processing email {email_id}: {e}")
                continue

        mail.logout()

    except Exception as e:
        print(f"Error polling inbox: {e}")

def main():
    """Main function to run the mail gateway service."""
    print("Starting Mail Gateway Service...")

    # Initialize database
    init_db()

    poll_interval = int(os.getenv('MAIL_POLL_INTERVAL', '60'))

    print(f"Polling interval: {poll_interval} seconds")

    while True:
        print("Checking for new emails...")
        poll_inbox()
        time.sleep(poll_interval)

if __name__ == '__main__':
    main()
