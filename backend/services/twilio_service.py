"""Twilio WhatsApp service for sending messages with media."""

from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp(phone_number: str, message: str, poster_url: str = None) -> str:
    """
    Send a WhatsApp message with optional image attachment.
    
    Args:
        phone_number: Recipient phone number (e.g., "+919876543210")
        message: Message text
        poster_url: Optional URL to image/poster to attach
        
    Returns:
        Message SID from Twilio
    """
    try:
        # Ensure phone number has country code and whatsapp: prefix
        if not phone_number.startswith("whatsapp:"):
            if not phone_number.startswith("+"):
                phone_number = f"+91{phone_number}"
            phone_number = f"whatsapp:{phone_number}"
        
        kwargs = {
            "from_": TWILIO_WHATSAPP_NUMBER,
            "to": phone_number,
            "body": message,
        }
        
        # Add media if poster URL provided
        if poster_url:
            kwargs["media_url"] = poster_url
        
        msg = client.messages.create(**kwargs)
        return msg.sid
    except Exception as e:
        print(f"Error sending WhatsApp to {phone_number}: {str(e)}")
        raise
