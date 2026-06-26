import requests
import os 
from datetime import datetime, timedelta


def send_otp_email(recipient_email, otp):
    url = "https://api.emailjs.com/api/v1.0/email/send"

    payload = {
        "service_id": os.getenv("EMAIL_SERVICE_ID"),
        "template_id": os.getenv("EMAILJS_TEMPLATE_ID"),
        "user_id": os.getenv("EMAILJS_PUBLIC_KEY"),
        "template_params": {
            "otp": otp,
            "to_email": recipient_email,
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f"EmailJS error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False