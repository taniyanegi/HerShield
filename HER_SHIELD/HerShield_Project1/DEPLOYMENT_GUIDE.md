# 🚀 HerShield Deployment Guide

This guide will help you deploy the HerShield application to various platforms.

## 📋 Prerequisites

- Python 3.11 or higher
- Git installed
- API keys for required services

## 🔑 Required API Keys

### 1. Gemini AI API Key
- Visit: https://makersuite.google.com/app/apikey
- Create a new API key
- Copy the key for later use

### 2. Twilio API (for SMS functionality)
- Sign up: https://www.twilio.com/
- Get Account SID and Auth Token
- Get a Twilio phone number
- Note down all three values

### 3. OpenWeatherMap API (optional)
- Sign up: https://openweathermap.org/api
- Get free API key
- Add to configuration

## 🏠 Local Deployment

### Step 1: Setup Environment
```bash
# Clone the repository
git clone <your-repo-url>
cd HerShield_Project1

# Install dependencies
pip install -r requirements.txt

# Run deployment script
python deploy.py
```

### Step 2: Configure Environment Variables
```bash
# Create .env file
cp env_example.txt .env

# Edit .env file with your API keys
# Use any text editor to add your actual API keys
```

### Step 3: Run Application
```bash
# Development mode
python app.py

# Production mode
gunicorn app:app --worker-class gevent --workers 4 --bind 0.0.0.0:8000
```

### Step 4: Access Application
- Open browser: http://localhost:5000
- Register new account
- Add emergency contacts
- Test all features

## ☁️ Cloud Deployment

### Option 1: Heroku Deployment

#### Step 1: Install Heroku CLI
- Download from: https://devcenter.heroku.com/articles/heroku-cli
- Install and login: `heroku login`

#### Step 2: Create Heroku App
```bash
# Create new app
heroku create your-app-name

# Add buildpack for Python
heroku buildpacks:set heroku/python
```

#### Step 3: Set Environment Variables
```bash
heroku config:set SECRET_KEY=your-secret-key-here
heroku config:set GEMINI_API_KEY=your-gemini-api-key
heroku config:set TWILIO_ACCOUNT_SID=your-twilio-sid
heroku config:set TWILIO_AUTH_TOKEN=your-twilio-token
heroku config:set TWILIO_PHONE_NUMBER=your-twilio-number
heroku config:set WEATHER_API_KEY=your-weather-key
```

#### Step 4: Deploy
```bash
git add .
git commit -m "Deploy HerShield application"
git push heroku main

# Open the app
heroku open
```

### Option 2: Railway Deployment

#### Step 1: Connect to Railway
- Visit: https://railway.app/
- Sign up with GitHub
- Click "New Project"
- Select "Deploy from GitHub repo"

#### Step 2: Configure Environment
- Add all environment variables in Railway dashboard
- Set the same variables as Heroku deployment

#### Step 3: Deploy
- Railway will automatically deploy your application
- Get the deployment URL from dashboard

### Option 3: Render Deployment

#### Step 1: Connect to Render
- Visit: https://render.com/
- Sign up and connect GitHub
- Click "New Web Service"

#### Step 2: Configure Service
- Select your repository
- Set build command: `pip install -r requirements.txt`
- Set start command: `gunicorn app:app`
- Add environment variables

#### Step 3: Deploy
- Click "Create Web Service"
- Render will deploy automatically

### Option 4: Vercel Deployment

#### Step 1: Install Vercel CLI
```bash
npm i -g vercel
```

#### Step 2: Deploy
```bash
vercel
# Follow the prompts
# Add environment variables when asked
```

## 🔧 Environment Variables Reference

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=False

# Gemini AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Twilio Configuration (for SMS)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number

# Weather API Configuration
WEATHER_API_KEY=your-openweathermap-api-key
```

## 🧪 Testing Deployment

### 1. Basic Functionality Test
- [ ] User registration works
- [ ] User login works
- [ ] Dashboard loads properly
- [ ] Emergency contacts can be added
- [ ] SOS button responds to clicks

### 2. Advanced Features Test
- [ ] Chatbot opens and responds
- [ ] Emergency contacts validation works
- [ ] SMS functionality (if Twilio configured)
- [ ] Weather API integration
- [ ] Location services work

### 3. Security Test
- [ ] Passwords are hashed
- [ ] Session management works
- [ ] Input validation prevents malicious data
- [ ] SQL injection protection works

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Errors
```bash
# Reinitialize database
python deploy.py
```

#### 2. API Key Errors
- Check all environment variables are set
- Verify API keys are valid
- Test API keys separately

#### 3. SMS Not Working
- Verify Twilio credentials
- Check Twilio phone number format
- Ensure account has credits

#### 4. Chatbot Not Responding
- Check Gemini API key
- Verify internet connection
- Check API quota limits

#### 5. Deployment Failures
- Check all files are committed
- Verify Procfile exists
- Check requirements.txt is complete

### Debug Commands
```bash
# Check application logs
heroku logs --tail

# Check environment variables
heroku config

# Restart application
heroku restart

# Check database
sqlite3 database/users.db ".tables"
```

## 📊 Monitoring

### Health Check Endpoints
- `/` - Main application
- `/health` - Health check (if implemented)
- `/admin` - Admin panel (for monitoring)

### Log Monitoring
- Check application logs regularly
- Monitor error rates
- Track user activity

## 🔄 Updates and Maintenance

### Updating Application
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Redeploy
git add .
git commit -m "Update application"
git push heroku main
```

### Database Backups
```bash
# Backup database
cp database/users.db database/users_backup.db
cp database/alerts.db database/alerts_backup.db
```

## 🎯 Production Checklist

- [ ] All environment variables set
- [ ] Database initialized
- [ ] SSL certificate configured
- [ ] Error logging enabled
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Security headers configured
- [ ] Performance optimized
- [ ] Documentation updated

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section
2. Review application logs
3. Verify all configurations
4. Contact support team

---

**Happy Deploying! 🚀** 