try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.date import DateTrigger
except ImportError:
    print("APScheduler is not installed. Please run: pip install APScheduler")
    raise

from datetime import datetime, timedelta
import json
import uuid
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Constants --- #
EVENTS_FILE = 'events.json'
REGISTRATIONS_FILE = 'registrations.json'
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@gmail.com"  # Replace with your Gmail
SENDER_PASSWORD = "your-app-password"   # Replace with your app password

# --- Email Templates --- #
REMINDER_EMAIL_TEMPLATE = """
🎯 Event Reminder: {event_name}

This is your {when} reminder!

Event Details:
📅 Date: {event_date}
⏰ Time: {event_time}
📍 Location: {event_location}

We look forward to seeing you there!

Best regards,
Event Management Team
"""


# --- Utility Functions --- #
def load_events():
    """Load events from the events file."""
    try:
        with open(EVENTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def send_reminder_email(recipient_email, event_data, when):
    """Send reminder email to participant."""
    try:
        message = MIMEMultipart()
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email
        message["Subject"] = f"Reminder: {event_data['name']} is {when} away!"

        body = REMINDER_EMAIL_TEMPLATE.format(
            event_name=event_data['name'],
            when=when,
            event_date=event_data['date'],
            event_time=event_data.get('time', 'TBD'),
            event_location=event_data.get('location', 'TBD')
        )

        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
        return True
    except Exception as e:
        logging.error(f"Failed to send reminder email: {str(e)}")
        return False


def load_registrations():
    """Load registrations from file."""
    try:
        with open(REGISTRATIONS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def reminder_callback(event_id, when):
    """Send reminder emails to all registered participants."""
    events = load_events()
    registrations = load_registrations()
    
    event = events.get(event_id)
    if not event:
        return

    # Get all registrations for this event
    event_registrations = [
        reg for reg in registrations.values()
        if reg['event_id'] == event_id
    ]

    # Send reminder to each registered participant
    for registration in event_registrations:
        send_reminder_email(registration['email'], event, when)


# --- Scheduler Functions --- #
def schedule_reminders(scheduler, event_id, event_date_str):
    """Schedule reminders for an event."""
    # Parse the event date
    event_date = datetime.fromisoformat(event_date_str)

    # 24-hour-before reminder
    reminder_1 = event_date - timedelta(days=1)
    if reminder_1 > datetime.now():
        scheduler.add_job(
            reminder_callback,
            trigger=DateTrigger(run_date=reminder_1),
            args=[event_id, "24-hour"],
            id=f"{event_id}_reminder1"
        )

    # 1-hour-before reminder
    reminder_2 = event_date - timedelta(hours=1)
    if reminder_2 > datetime.now():
        scheduler.add_job(
            reminder_callback,
            trigger=DateTrigger(run_date=reminder_2),
            args=[event_id, "1-hour"],
            id=f"{event_id}_reminder2"
        )


def init_scheduler():
    """Initialize the background scheduler and reschedule existing reminders."""
    scheduler = BackgroundScheduler()
    scheduler.start()

    # On startup, reschedule reminders for all future events
    events = load_events()
    for event_id, ev in events.items():
        schedule_reminders(scheduler, event_id, ev['date'])

    return scheduler


# --- Event Handling --- #
# expose a function to call when you create a new event
scheduler = init_scheduler()


def on_event_created(event_id, date):
    """Handle scheduling of event reminders."""
    try:
        logging.info(f"Scheduling reminder for event {event_id} on {date}")
        schedule_reminders(scheduler, event_id, date)
        return True
    except Exception as e:
        logging.error(f"Failed to schedule reminder: {str(e)}")
        return False
