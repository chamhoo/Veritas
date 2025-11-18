import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add shared module to path
sys.path.insert(0, '/root/Veritas')

from dotenv import load_dotenv

from shared.mq_utils import consume_messages, FILTERED_CONTENT_QUEUE

load_dotenv()

def send_email(to_email, subject, body):
    """Send an email notification to the user."""
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    # Create message
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    # Add body
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

        print(f"Email sent successfully to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication failed: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
        return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def process_notification(ch, method, properties, body):
    """Process a notification message and send email."""
    try:
        message = json.loads(body)

        task_id = message.get('task_id')
        user_email = message.get('user_email')
        subject = message.get('subject')
        email_body = message.get('body')

        print(f"Sending notification for task {task_id} to {user_email}")

        # Send the email
        success = send_email(user_email, subject, email_body)

        if success:
            print(f"Notification sent successfully for task {task_id}")
        else:
            print(f"Failed to send notification for task {task_id}")

        # Acknowledge the message (even on failure to avoid infinite retries)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError as e:
        print(f"Error decoding message: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing notification: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    """Main function to run the notifier service."""
    print("Starting Notifier Service...")

    # Validate SMTP configuration
    required_vars = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"Warning: Missing SMTP configuration: {', '.join(missing)}")
        print("Emails may fail to send.")

    print("Listening for messages on filtered_content_queue...")

    # Start consuming messages
    consume_messages(FILTERED_CONTENT_QUEUE, process_notification)

if __name__ == '__main__':
    main()
