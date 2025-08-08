#!/usr/bin/env python3
"""
Deployment script for HerShield application
This script sets up the database and initializes the application
"""

import sqlite3
import os
import sys

def create_directories():
    """Create necessary directories"""
    directories = ['database', 'logs']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

def init_database():
    """Initialize the database with required tables"""
    try:
        # Create users database
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      email TEXT UNIQUE NOT NULL,
                      phone TEXT NOT NULL,
                      password TEXT NOT NULL)''')
        
        # Emergency contacts table
        c.execute('''CREATE TABLE IF NOT EXISTS emergency_contacts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      name TEXT NOT NULL,
                      phone TEXT NOT NULL,
                      relationship TEXT,
                      priority INTEGER DEFAULT 1,
                      FOREIGN KEY (user_id) REFERENCES users (id))''')
        
        # User experiences table
        c.execute('''CREATE TABLE IF NOT EXISTS user_experiences
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      title TEXT NOT NULL,
                      content TEXT NOT NULL,
                      category TEXT NOT NULL,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      likes INTEGER DEFAULT 0,
                      FOREIGN KEY (user_id) REFERENCES users (id))''')
        
        conn.commit()
        conn.close()
        print("✓ Users database initialized successfully")
        
        # Create alerts database
        conn = sqlite3.connect('database/alerts.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS alerts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      name TEXT NOT NULL,
                      location TEXT NOT NULL,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      status TEXT DEFAULT 'active',
                      priority TEXT DEFAULT 'normal')''')
        
        conn.commit()
        conn.close()
        print("✓ Alerts database initialized successfully")
        
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)

def check_dependencies():
    """Check if all required dependencies are available"""
    try:
        import flask
        import google.generativeai
        import twilio
        import requests
        print("✓ All dependencies are available")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

def main():
    """Main deployment function"""
    print("🚀 Starting HerShield deployment...")
    print("=" * 50)
    
    # Check dependencies
    check_dependencies()
    
    # Create directories
    create_directories()
    
    # Initialize database
    init_database()
    
    print("=" * 50)
    print("✅ Deployment completed successfully!")
    print("\n📋 Next steps:")
    print("1. Set up environment variables (see env_example.txt)")
    print("2. Configure your API keys (Gemini, Twilio, Weather)")
    print("3. Run the application: python app.py")
    print("4. For production: gunicorn app:app")

if __name__ == "__main__":
    main() 