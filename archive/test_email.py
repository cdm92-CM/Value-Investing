import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_test():
    print(f"Testing email connection for {EMAIL_ADDRESS}...")
    msg = EmailMessage()
    msg['Subject'] = "Sentinel Connection Test"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg.set_content("Success! Your Retirement Sentinel can now send you alerts.")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("✅ Email sent! Check your inbox.")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    send_test()
    