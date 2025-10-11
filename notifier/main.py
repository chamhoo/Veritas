import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
sys.path.append('/app')

from shared.mq_utils import consume_queue

# Configure email settings
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)

def send_email(to_email, subject, body):
    """Send an email via SMTP"""
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD]):
        print("Error: SMTP configuration is incomplete")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def process_message(message):
    """Process a message from the filtered_content_queue"""
    user_email = message.get('user_email')
    subject = message.get('formatted_subject')
    body = message.get('formatted_body')
    
    if not all([user_email, subject, body]):
        print("Error: Invalid message format")
        return
    
    print(f"Sending notification to {user_email}")
    send_email(user_email, subject, body)

def main():
    """Main function to consume messages from filtered_content_queue"""
    print("Notifier service started")
    consume_queue("filtered_content_queue", process_message)

if __name__ == "__main__":
    main()
