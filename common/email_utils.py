import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from common.config import Config

class EmailClient:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.smtp_user = Config.SMTP_USER
        self.smtp_pass = Config.SMTP_PASS

    def send_email(self, recipient_email: str, subject: str, body: str):
        if not self.smtp_user:
            print("SMTP credentials not configured. Skipping email send.")
            return
            
        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            print(f"Email sent successfully to {recipient_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")
