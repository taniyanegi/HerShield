from twilio_alert import send_sms

def send_sos_alert(phone_number, message):
    """
    Send an SOS alert to the specified phone number.
    
    Args:
        phone_number (str): The phone number to send the alert to
        message (str): The emergency message to send
    
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    return send_sms(phone_number, message)
