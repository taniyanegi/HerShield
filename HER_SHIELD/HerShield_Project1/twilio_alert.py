from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'AC4b1dc92f50e014226bf9530c7fca4c63')
auth_token = os.getenv('TWILIO_AUTH_TOKEN', 'c5761d8c607821b86870e9878f25bfaa')
from_number = os.getenv('TWILIO_PHONE_NUMBER', '+19062562899')

def send_sms(to_number, message):
    """
    Send an SMS message using Twilio.
    
    Args:
        to_number (str): The recipient's phone number
        message (str): The message to send
    
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    try:
        # Format phone number (add country code if not present)
        if not to_number.startswith('+'):
            to_number = '+91' + to_number.lstrip('0')  # Add India country code by default
        
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Send message with high priority
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
            # Add priority for emergency messages
            status_callback=os.getenv('TWILIO_STATUS_CALLBACK_URL', None)
        )
        
        print(f"✅ Emergency SMS sent successfully to {to_number}")
        print(f"📱 Message SID: {message_obj.sid}")
        print(f"📊 Message Status: {message_obj.status}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending SMS to {to_number}: {str(e)}")
        # Print more detailed error information
        if hasattr(e, 'msg'):
            print(f"🔍 Error message: {e.msg}")
        if hasattr(e, 'code'):
            print(f"🔢 Error code: {e.code}")
        return False

def send_emergency_alert(to_number, user_name, location, timestamp, relationship):
    """
    Send a formatted emergency alert SMS.
    
    Args:
        to_number (str): The recipient's phone number
        user_name (str): Name of the person in emergency
        location (dict): Location coordinates
        timestamp (str): Time of emergency
        relationship (str): Relationship with the person
    
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    try:
        # Create urgent emergency message
        emergency_message = f"""🚨 EMERGENCY ALERT! 🚨

URGENT: {user_name} is in danger and has triggered an SOS alert!

Your relationship with {user_name} requires immediate attention!

📍 Current Location: https://maps.google.com/?q={location['latitude']},{location['longitude']}
⏰ Time: {timestamp}

⚠️ PLEASE RESPOND IMMEDIATELY! ⚠️
• Try to contact {user_name} immediately
• If no response, contact local authorities
• Share this location with trusted family members
• Keep this number active for updates

This is an automated emergency alert from HerShield.
Stay safe! 🛡️"""

        # Send the emergency message
        success = send_sms(to_number, emergency_message)
        
        if success:
            # Send follow-up instructions after a short delay
            follow_up_message = f"""📋 Follow-up Instructions for {user_name}'s Emergency:

1️⃣ IMMEDIATE ACTIONS:
   • Call {user_name} multiple times
   • Send text messages asking for response
   • Check social media for any activity

2️⃣ IF NO RESPONSE:
   • Contact local police (100)
   • Call nearby hospitals
   • Alert family members and friends

3️⃣ LOCATION DETAILS:
   • GPS: {location['latitude']}, {location['longitude']}
   • Google Maps: https://maps.google.com/?q={location['latitude']},{location['longitude']}

4️⃣ STAY CONNECTED:
   • Keep your phone charged
   • Respond to any updates from {user_name}
   • Share this information with trusted contacts

🆘 This is a real emergency - please act quickly!"""

            # Send follow-up message
            send_sms(to_number, follow_up_message)
        
        return success
        
    except Exception as e:
        print(f"❌ Error sending emergency alert to {to_number}: {str(e)}")
        return False

def send_alert_confirmation(to_number, user_name, contacts_notified):
    """
    Send confirmation message to the user who triggered the alert.
    
    Args:
        to_number (str): The user's phone number
        user_name (str): Name of the user
        contacts_notified (int): Number of contacts notified
    
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    try:
        confirmation_message = f"""✅ SOS Alert Confirmation

Dear {user_name},

Your emergency SOS alert has been successfully sent to {contacts_notified} emergency contacts.

📱 Your contacts have been notified with:
• Your current location
• Emergency instructions
• Contact information

🛡️ Help is on the way! Stay safe and try to:
• Move to a safe location if possible
• Keep your phone charged
• Respond to calls from your contacts

This message is from HerShield - your safety companion."""

        return send_sms(to_number, confirmation_message)
        
    except Exception as e:
        print(f"❌ Error sending confirmation to {to_number}: {str(e)}")
        return False
