"""
email_service.py
-----------------
Simulated email sender. In a real deployment you'd swap the body of
`send_email_simulation` for an actual SMTP / SendGrid / SES call — the
function signature stays the same so nothing else in the app needs to
change. For the FYP demo, it:
  1. Prints a formatted "email" to the server console/log.
  2. Persists a row in `notifications` (channel='email_sim') so it is
     visible in the user's notification inbox in the UI.
"""

from datetime import datetime
from models.notification_model import create_notification


def send_email_simulation(user_id: int, subject: str, body: str, emergency_id: int = None):
    """Simulate sending an email and log it as a notification."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 70)
    print(f"[SIMULATED EMAIL]  {timestamp}")
    print(f"To (user_id): {user_id}")
    print(f"Subject: {subject}")
    print("-" * 70)
    print(body)
    print("=" * 70)

    message = f"{subject}: {body}"
    create_notification(user_id=user_id, message=message, channel="email_sim", emergency_id=emergency_id)


def notify_emergency_contacts_simulation(contacts, user_full_name, emergency_type, lat, lng):
    """
    Simulates notifying each emergency contact (SMS/email) that the user
    has triggered an SOS. `contacts` is a list of dicts with contact_name
    and contact_phone (from emergency_contacts table).
    """
    maps_link = f"https://www.google.com/maps?q={lat},{lng}"
    for contact in contacts:
        print("=" * 70)
        print(f"[SIMULATED SMS/EMAIL to {contact['contact_name']} - {contact['contact_phone']}]")
        print(f"{user_full_name} has triggered a {emergency_type.upper()} emergency SOS.")
        print(f"Live location: {maps_link}")
        print("=" * 70)
