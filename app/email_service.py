import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config
from datetime import datetime

class EmailService:
    def __init__(self):
        self.config = Config()

    def send_email(self, to_email, subject, body):
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'html'))

            # Connect to server and send
            with smtplib.SMTP(self.config.EMAIL_HOST, self.config.EMAIL_PORT) as server:
                server.starttls()
                server.login(self.config.EMAIL_USERNAME, self.config.EMAIL_PASSWORD)
                server.send_message(msg)
            
            print(f"Email sent to {to_email} at {datetime.now()}")
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def send_medication_reminder(self, patient_email, medicine_name, dosage, time_of_day):
        subject = f"MedTrack Reminder: Time to take your {medicine_name}"
        
        body = f"""
        <html>
            <body>
                <h2>Medication Reminder</h2>
                <p>Hello,</p>
                <p>This is a reminder to take your medication:</p>
                <ul>
                    <li><strong>Medicine:</strong> {medicine_name}</li>
                    <li><strong>Dosage:</strong> {dosage}</li>
                    <li><strong>Time:</strong> {time_of_day.capitalize()}</li>
                </ul>
                <p>Please remember to mark this as taken in your MedTrack app after you've taken it.</p>
                <p>Best regards,<br>MedTrack Team</p>
            </body>
        </html>
        """
        
        return self.send_email(patient_email, subject, body)