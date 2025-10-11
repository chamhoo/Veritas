import os
import time
import imaplib
import email
import re
import sqlalchemy
from email.header import decode_header
from email.utils import parseaddr
from sqlalchemy.orm import Session
import sys
sys.path.append('/app')

from shared.database import get_db, engine
from shared.models import Base, Task
from shared.mq_utils import publish_message

# Initialize database
Base.metadata.create_all(bind=engine)

# Configure email settings
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # seconds

def decode_email_subject(encoded_subject):
    """Decode email subject"""
    decoded_list = decode_header(encoded_subject)
    subject = ""
    for text, encoding in decoded_list:
        if isinstance(text, bytes):
            try:
                subject += text.decode(encoding or 'utf-8')
            except:
                subject += text.decode('utf-8', errors='replace')
        else:
            subject += text
    return subject

def extract_task_id(body):
    """Extract task ID from email body"""
    task_id_pattern = r"Task ID: (\d+)"
    match = re.search(task_id_pattern, body)
    if match:
        return int(match.group(1))
    return None

def create_initial_prompt(request_body):
    """Generate an initial filtering prompt based on user request"""
    base_prompt = f"""
    You are an intelligent content filter. Your job is to analyze content and determine 
    if it matches the following user request:
    
    "{request_body}"
    
    When presented with content, you must decide if it is relevant to this request.
    Respond with YES if it's relevant, NO if it's not relevant.
    Provide a brief explanation of your decision.
    """
    return base_prompt.strip()

def process_new_task(db: Session, from_email, email_body):
    """Process a new task request"""
    lines = email_body.strip().split('\n')
    if not lines:
        return "Please provide task details in the email body."
    
    # Extract source type and target from the first line
    request_text = lines[0].strip()
    
    # Default to Reddit if no source type is specified
    source_type = "reddit"
    source_target = request_text
    
    # Check for specific source types
    if "reddit" in request_text.lower() and "r/" in request_text:
        source_type = "reddit"
        # Extract subreddit name
        matches = re.search(r'r/(\w+)', request_text)
        if matches:
            source_target = f"r/{matches.group(1)}"
    elif "http" in request_text and ("feed" in request_text.lower() or "rss" in request_text.lower()):
        source_type = "rss"
        # Extract URL
        matches = re.search(r'(https?://\S+)', request_text)
        if matches:
            source_target = matches.group(1)
    
    # Generate initial prompt
    initial_prompt = create_initial_prompt(request_text)
    
    # Create new task
    new_task = Task(
        user_email=from_email,
        source_type=source_type,
        source_target=source_target,
        current_prompt=initial_prompt,
        status='active'
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return f"Task created successfully. Task ID: {new_task.task_id}. We'll monitor {source_target} for you."

def process_list_tasks(db: Session, from_email):
    """List all tasks for a user"""
    tasks = db.query(Task).filter(Task.user_email == from_email).all()
    
    if not tasks:
        return "You don't have any tasks."
    
    result = "Your tasks:\n\n"
    for task in tasks:
        result += f"Task ID: {task.task_id}\n"
        result += f"Source: {task.source_type} - {task.source_target}\n"
        result += f"Status: {task.status}\n\n"
    
    return result

def process_pause_task(db: Session, from_email, email_body):
    """Pause a specific task"""
    task_id = None
    match = re.search(r'(\d+)', email_body)
    if match:
        task_id = int(match.group(1))
    else:
        return "Please provide a task ID."
    
    task = db.query(Task).filter(Task.task_id == task_id, Task.user_email == from_email).first()
    if not task:
        return f"Task with ID {task_id} not found or you don't have permission."
    
    task.status = 'paused'
    db.commit()
    
    return f"Task {task_id} has been paused."

def process_resume_task(db: Session, from_email, email_body):
    """Resume a paused task"""
    task_id = None
    match = re.search(r'(\d+)', email_body)
    if match:
        task_id = int(match.group(1))
    else:
        return "Please provide a task ID."
    
    task = db.query(Task).filter(Task.task_id == task_id, Task.user_email == from_email).first()
    if not task:
        return f"Task with ID {task_id} not found or you don't have permission."
    
    task.status = 'active'
    db.commit()
    
    return f"Task {task_id} has been resumed."

def process_delete_task(db: Session, from_email, email_body):
    """Delete a task"""
    task_id = None
    match = re.search(r'(\d+)', email_body)
    if match:
        task_id = int(match.group(1))
    else:
        return "Please provide a task ID."
    
    task = db.query(Task).filter(Task.task_id == task_id, Task.user_email == from_email).first()
    if not task:
        return f"Task with ID {task_id} not found or you don't have permission."
    
    db.delete(task)
    db.commit()
    
    return f"Task {task_id} has been deleted."

def process_feedback(db: Session, from_email, email_body, task_id):
    """Process feedback on a task notification"""
    task = db.query(Task).filter(Task.task_id == task_id, Task.user_email == from_email).first()
    if not task:
        return f"Task with ID {task_id} not found or you don't have permission."
    
    # Send the feedback to the feedback processor
    publish_message("feedback_queue", {
        "task_id": task_id,
        "feedback_text": email_body,
        "current_prompt": task.current_prompt
    })
    
    return f"Thank you for your feedback on task {task_id}. We'll use it to improve your results."

def check_email():
    """Check email inbox for new messages and process them"""
    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USERNAME, IMAP_PASSWORD)
        mail.select('inbox')
        
        # Search for all unread emails
        status, data = mail.search(None, '(UNSEEN)')
        if status != 'OK':
            print("No messages found!")
            return
        
        for num in data[0].split():
            # Fetch email data
            status, data = mail.fetch(num, '(RFC822)')
            if status != 'OK':
                continue
                
            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Get From, Subject, and In-Reply-To fields
            from_addr = parseaddr(email_message["From"])[1]
            subject = decode_email_subject(email_message["Subject"]) if email_message["Subject"] else ""
            in_reply_to = email_message["In-Reply-To"]
            
            # Get email body
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
            else:
                try:
                    body = email_message.get_payload(decode=True).decode()
                except:
                    body = email_message.get_payload(decode=True).decode('utf-8', errors='replace')
            
            # Process command based on subject and whether it's a reply
            db = next(get_db())
            
            response = None
            try:
                if in_reply_to:  # This is a reply to a previous email
                    task_id = extract_task_id(body)
                    if task_id:
                        response = process_feedback(db, from_addr, body, task_id)
                    else:
                        response = "Could not identify which task you're providing feedback for."
                else:  # This is a new command email
                    subject_lower = subject.lower()
                    if "new task" in subject_lower:
                        response = process_new_task(db, from_addr, body)
                    elif "list task" in subject_lower:
                        response = process_list_tasks(db, from_addr)
                    elif "pause task" in subject_lower:
                        response = process_pause_task(db, from_addr, body)
                    elif "resume task" in subject_lower:
                        response = process_resume_task(db, from_addr, body)
                    elif "delete task" in subject_lower:
                        response = process_delete_task(db, from_addr, body)
                    else:
                        response = "Unknown command. Please use one of: New Task, List Tasks, Pause Task, Resume Task, Delete Task."
            except Exception as e:
                response = f"An error occurred: {str(e)}"
                print(f"Error processing email: {e}")
            finally:
                db.close()
            
            # Mark email as read
            mail.store(num, '+FLAGS', '\\Seen')
            
            # If there's a response, send it via the notification queue
            if response:
                publish_message("filtered_content_queue", {
                    "user_email": from_addr,
                    "formatted_subject": f"Re: {subject}",
                    "formatted_body": response,
                    "task_id_for_feedback": None  # This is a response, not a task notification
                })
                
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error checking email: {e}")

def main():
    """Main function to periodically check email"""
    print("Mail Gateway service started")
    while True:
        try:
            check_email()
        except Exception as e:
            print(f"Error in main loop: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
