from datetime import datetime, timedelta
from typing import Dict, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database.database import SessionLocal
from database.models import Appointment, User, ServiceProvider

class NotificationSystem:
    def __init__(self):
        self.email_sender = "noreply@example.com"  # Replace with your email
        
    def send_confirmation(self, appointment_details: Dict) -> bool:
        """
        Send appointment confirmation
        """
        subject = "Appointment Confirmation"
        body = f"""
        Your appointment has been confirmed!
        
        Details:
        Provider: {appointment_details['provider']}
        Date: {appointment_details['date']}
        Time: {appointment_details['time']}
        
        Please arrive 10 minutes before your scheduled time.
        To cancel or reschedule, please contact us.
        
        Thank you for using our service!
        """
        
        return self._send_email(appointment_details['email'], subject, body)
        
    def send_reminder(self, appointment: Appointment) -> bool:
        """
        Send appointment reminder
        """
        subject = "Appointment Reminder"
        body = f"""
        This is a reminder for your upcoming appointment:
        
        Provider: {appointment.provider.name}
        Date: {appointment.datetime.strftime('%Y-%m-%d')}
        Time: {appointment.datetime.strftime('%I:%M %p')}
        
        Please arrive 10 minutes before your scheduled time.
        
        Thank you for using our service!
        """
        
        return self._send_email(appointment.user.email, subject, body)
        
    def check_and_send_reminders(self):
        """
        Check for upcoming appointments and send reminders
        """
        try:
            with SessionLocal() as db:
                # Get appointments in the next 24 hours
                tomorrow = datetime.now() + timedelta(days=1)
                upcoming = db.query(Appointment).filter(
                    Appointment.datetime <= tomorrow,
                    Appointment.datetime >= datetime.now()
                ).all()
                
                for appointment in upcoming:
                    self.send_reminder(appointment)
                    
        except Exception as e:
            print(f"Error sending reminders: {e}")
            
    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send email using local SMTP (for development)
        In production, use a proper email service
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # For development, print the email
            print(f"\nEmail Notification:")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n{body}")
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False 