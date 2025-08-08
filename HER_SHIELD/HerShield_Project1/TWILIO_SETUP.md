# 📱 Twilio SMS Setup Guide for HerShield

## 🚀 Quick Setup

To enable real-time SMS notifications for the SOS feature, you need to configure Twilio credentials.

### 1. Get Twilio Account

1. Sign up at [Twilio Console](https://console.twilio.com/)
2. Get your Account SID and Auth Token
3. Purchase a phone number for sending SMS

### 2. Environment Variables

Create a `.env` file in the project root with:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=your-account-sid-here
TWILIO_AUTH_TOKEN=your-auth-token-here
TWILIO_PHONE_NUMBER=your-twilio-phone-number-here

# Other required variables
SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key-here
```

### 3. Install Dependencies

```bash
pip install twilio python-dotenv
```

## 🔧 Configuration Details

### Twilio Credentials

- **Account SID**: Found in your Twilio Console dashboard
- **Auth Token**: Found in your Twilio Console dashboard  
- **Phone Number**: Your Twilio phone number (format: +1234567890)

### SMS Features

✅ **Emergency Alerts**: Sent when SOS is triggered (3 clicks)  
✅ **Location Sharing**: GPS coordinates with Google Maps link  
✅ **Follow-up Instructions**: Detailed emergency response steps  
✅ **User Confirmation**: SMS sent to user confirming alert sent  
✅ **Priority Messaging**: High-priority emergency notifications  

## 📋 SMS Message Format

### Emergency Alert Message
```
🚨 EMERGENCY ALERT! 🚨

URGENT: [User Name] is in danger and has triggered an SOS alert!

Your relationship with [User Name] requires immediate attention!

📍 Current Location: https://maps.google.com/?q=[lat],[lng]
⏰ Time: [timestamp]

⚠️ PLEASE RESPOND IMMEDIATELY! ⚠️
• Try to contact [User Name] immediately
• If no response, contact local authorities
• Share this location with trusted family members
• Keep this number active for updates

This is an automated emergency alert from HerShield.
Stay safe! 🛡️
```

### Follow-up Instructions
```
📋 Follow-up Instructions for [User Name]'s Emergency:

1️⃣ IMMEDIATE ACTIONS:
   • Call [User Name] multiple times
   • Send text messages asking for response
   • Check social media for any activity

2️⃣ IF NO RESPONSE:
   • Contact local police (100)
   • Call nearby hospitals
   • Alert family members and friends

3️⃣ LOCATION DETAILS:
   • GPS: [lat], [lng]
   • Google Maps: https://maps.google.com/?q=[lat],[lng]

4️⃣ STAY CONNECTED:
   • Keep your phone charged
   • Respond to any updates from [User Name]
   • Share this information with trusted contacts

🆘 This is a real emergency - please act quickly!
```

## 🛡️ Security Features

- ✅ **Environment Variables**: Secure credential storage
- ✅ **Error Handling**: Graceful failure handling
- ✅ **Message Validation**: Phone number formatting
- ✅ **Delivery Status**: Message delivery tracking
- ✅ **Rate Limiting**: Prevents spam

## 🧪 Testing

### Test SMS Function
```python
from twilio_alert import send_sms

# Test message
success = send_sms("+91XXXXXXXXXX", "Test emergency alert from HerShield")
print(f"Message sent: {success}")
```

### Test Emergency Alert
```python
from twilio_alert import send_emergency_alert

# Test emergency alert
location = {"latitude": 12.9716, "longitude": 77.5946}  # Bangalore
success = send_emergency_alert(
    "+91XXXXXXXXXX", 
    "Test User", 
    location, 
    "2024-01-01 12:00:00", 
    "Family"
)
print(f"Emergency alert sent: {success}")
```

## 📊 Monitoring

### Console Logs
The application logs all SMS activities:
- ✅ Successful sends
- ❌ Failed sends  
- 📱 Message SIDs
- 📊 Delivery status

### Twilio Console
Monitor messages in your Twilio Console:
- Message delivery status
- Error logs
- Usage statistics
- Phone number configuration

## 🔄 Troubleshooting

### Common Issues

1. **Invalid Phone Number Format**
   - Ensure numbers include country code (+91 for India)
   - Remove spaces and special characters

2. **Authentication Errors**
   - Verify Account SID and Auth Token
   - Check if credentials are in .env file

3. **Phone Number Not Verified**
   - Verify recipient numbers in Twilio Console (trial accounts)
   - Purchase credits for production use

4. **Message Delivery Failures**
   - Check recipient number format
   - Verify Twilio phone number is active
   - Check account balance

### Error Messages
```
❌ Error sending SMS to +91XXXXXXXXXX: [Error details]
🔍 Error message: [Specific error]
🔢 Error code: [Error code]
```

## 💰 Pricing

- **Trial Account**: Free credits for testing
- **Production**: Pay per message sent
- **Phone Numbers**: Monthly rental fee
- **International**: Additional charges for international SMS

## 🚀 Production Deployment

1. **Environment Variables**: Set in production environment
2. **Phone Number Verification**: Verify all recipient numbers
3. **Rate Limiting**: Implement to prevent abuse
4. **Monitoring**: Set up alerts for failures
5. **Backup**: Consider multiple SMS providers

## 📞 Support

- **Twilio Documentation**: https://www.twilio.com/docs
- **Twilio Support**: https://support.twilio.com/
- **HerShield Issues**: Report bugs in project repository

---

**Remember**: Keep your Twilio credentials secure and never commit them to version control! 🔒 