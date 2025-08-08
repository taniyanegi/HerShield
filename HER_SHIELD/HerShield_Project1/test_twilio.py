#!/usr/bin/env python3
"""
Test script to verify Twilio SMS functionality
"""

from twilio_alert import send_sms, send_emergency_alert, send_alert_confirmation
import os

def test_twilio_credentials():
    """Test basic Twilio functionality"""
    print("🧪 Testing Twilio SMS functionality...")
    
    # Test basic SMS
    test_message = "🧪 Test message from HerShield - Twilio integration is working!"
    test_phone = "+919876543210"  # Replace with a real test number
    
    print(f"📱 Testing basic SMS to {test_phone}")
    try:
        result = send_sms(test_phone, test_message)
        if result:
            print("✅ Basic SMS test PASSED")
        else:
            print("❌ Basic SMS test FAILED")
    except Exception as e:
        print(f"❌ Basic SMS test ERROR: {str(e)}")
    
    # Test emergency alert
    print("\n🚨 Testing emergency alert...")
    try:
        test_location = {
            'latitude': 28.6139,
            'longitude': 77.2090
        }
        result = send_emergency_alert(
            test_phone,
            "Test User",
            test_location,
            "2024-01-01T12:00:00Z",
            "Test Contact"
        )
        if result:
            print("✅ Emergency alert test PASSED")
        else:
            print("❌ Emergency alert test FAILED")
    except Exception as e:
        print(f"❌ Emergency alert test ERROR: {str(e)}")
    
    # Test confirmation message
    print("\n✅ Testing confirmation message...")
    try:
        result = send_alert_confirmation(test_phone, "Test User", 3)
        if result:
            print("✅ Confirmation message test PASSED")
        else:
            print("❌ Confirmation message test FAILED")
    except Exception as e:
        print(f"❌ Confirmation message test ERROR: {str(e)}")

if __name__ == "__main__":
    test_twilio_credentials() 