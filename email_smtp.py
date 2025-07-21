import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

def send_test_email():
    try:
        # Email configuration
        from_email = os.getenv("EMAIL_FROM")
        to_email = input("Enter recipient email: ").strip()
        password = os.getenv("EMAIL_PASSWORD")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = "MedTrack Email Test"
        
        body = f"""
        <html>
            <body>
                <h2>MedTrack Test Email</h2>
                <p>This is a test email sent at <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>.</p>
                <p>If you received this, your email setup is working!</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USERNAME"), password)
            server.send_message(msg)
        
        print(f"\n✅ Email sent to {to_email}!")
    
    except Exception as e:
        print(f"\n❌ Failed to send email: {str(e)}")

if __name__ == "__main__":
    print("Testing MedTrack Email System...")
    send_test_email()