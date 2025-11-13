"""
Notifier Service

Listens to filtered content queue and sends emails to users.
"""
import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import init_db
from shared.mq_utils import consume_messages


class Notifier:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.from_name = os.getenv("FROM_NAME", "Dynamic Pipeline")

        if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
            print("Warning: SMTP credentials not fully configured. Email sending will fail.")

    def send_email(self, to_email: str, subject: str, body: str, task_id: int = None):
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            task_id: Optional task ID for reply tracking
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            # Add Message-ID for reply tracking
            if task_id:
                msg["Message-ID"] = f"<task-{task_id}-{os.urandom(8).hex()}@{self.from_email.split('@')[1]}>"

            # Attach body
            msg.attach(MIMEText(body, "plain"))

            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            print(f"Email sent to {to_email}: {subject}")

        except Exception as e:
            print(f"Error sending email to {to_email}: {e}")
            raise

    def process_message(self, ch, method, properties, body):
        """
        Process a message from the filtered content queue.
        """
        try:
            data = json.loads(body)
            user_email = data.get("user_email")
            subject = data.get("subject")
            email_body = data.get("body")
            task_id = data.get("task_id")

            if not user_email or not subject or not email_body:
                print("Invalid message format")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Send email
            self.send_email(user_email, subject, email_body, task_id)

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"Error processing message: {e}")
            # Reject and requeue the message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start(self):
        """Start consuming messages."""
        print("Notifier started. Waiting for messages...")
        consume_messages("filtered_content_queue", self.process_message)


def main():
    # Initialize database (not strictly needed but good practice)
    print("Initializing database...")
    init_db()

    # Start notifier
    notifier = Notifier()
    notifier.start()


if __name__ == "__main__":
    main()
