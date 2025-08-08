from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from twilio_alert import send_sms, send_emergency_alert, send_alert_confirmation
import sqlite3
import datetime
import hashlib
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Gemini API setup
gemini_api_key = os.getenv('GEMINI_API_KEY', '188fe0a4de29ce2ecb2ee7cdfe3a2d0b')
genai.configure(api_key=gemini_api_key)

# Database setup functions
def get_db_connection():
    # Create database directory if it doesn't exist
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect('database/users.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_alert_connection():
    # Create database directory if it doesn't exist
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect('database/alerts.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Create database directory if it doesn't exist
    os.makedirs('database', exist_ok=True)
    
    # Initialize users database
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  phone TEXT NOT NULL,
                  password TEXT NOT NULL)''')
    
    # Create emergency contacts table
    c.execute('''CREATE TABLE IF NOT EXISTS emergency_contacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  phone TEXT NOT NULL,
                  relationship TEXT,
                  priority INTEGER DEFAULT 1,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create user experiences table
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
    
    # Initialize alerts database
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

# Initialize database
init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[4], password):
            session['user_id'] = user[0]
            session['name'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate password match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signup'))
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)',
                     (name, email, phone, hashed_password))
            conn.commit()
            conn.close()
            
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['name'])

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('landing'))

@app.route('/emergency', methods=['POST'])
def emergency():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = session
    location = request.form['location']

    send_sms(user['name'], location)

    conn = get_alert_connection()
    conn.execute('INSERT INTO alerts (name, location, timestamp) VALUES (?, ?, ?)',
                 (user['name'], location, datetime.datetime.now()))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/videos')
def videos():
    return render_template('videos.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html', user=session)

@app.route('/admin')
def admin():
    conn = get_alert_connection()
    alerts = conn.execute('SELECT * FROM alerts ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template('admin.html', alerts=alerts)

from emergency import send_sos_alert

@app.route('/sos', methods=['POST'])
def sos():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        data = request.get_json()
        location = data.get('location')
        timestamp = data.get('timestamp')
        emergency = data.get('emergency', True)

        if not location or not timestamp:
            return jsonify({'error': 'Missing location or timestamp'}), 400

        # Get user's emergency contacts
        conn = get_db_connection()
        contacts = conn.execute('''
            SELECT * FROM emergency_contacts 
            WHERE user_id = ? 
            ORDER BY priority
        ''', (session['user_id'],)).fetchall()
        
        # Get user details
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()

        if not contacts:
            return jsonify({
                'error': 'No emergency contacts found',
                'message': 'Please add emergency contacts in your profile',
                'contacts_notified': 0
            }), 200

        # Send urgent SMS to emergency contacts using improved Twilio functions
        notifications_sent = 0
        for contact in contacts:
            try:
                # Send formatted emergency alert with follow-up instructions
                if send_emergency_alert(
                    contact['phone'], 
                    user['name'], 
                    location, 
                    timestamp, 
                    contact['relationship']
                ):
                    notifications_sent += 1
                    print(f"✅ Emergency alert sent to {contact['name']} ({contact['phone']})")
                else:
                    print(f"❌ Failed to send emergency alert to {contact['name']} ({contact['phone']})")
                    
            except Exception as e:
                print(f"❌ Error sending SMS to {contact['name']}: {str(e)}")
                continue

        # Store alert in database with high priority
        conn = get_alert_connection()
        conn.execute('''
            INSERT INTO alerts (user_id, name, location, timestamp, status, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            user['name'],
            f"{location['latitude']},{location['longitude']}",
            timestamp,
            'active',
            'high'
        ))
        conn.commit()
        conn.close()

        # Send confirmation SMS to the user who triggered the alert
        try:
            send_alert_confirmation(user['phone'], user['name'], notifications_sent)
            print(f"✅ Confirmation SMS sent to {user['name']} ({user['phone']})")
        except Exception as e:
            print(f"❌ Error sending confirmation SMS to user: {str(e)}")

        return jsonify({
            'status': 'success',
            'message': 'Emergency alert sent successfully',
            'contacts_notified': notifications_sent,
            'total_contacts': len(contacts),
            'user_confirmed': True
        })

    except Exception as e:
        print(f"Error in SOS route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/update-location', methods=['POST'])
def update_location():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        data = request.get_json()
        location = data.get('location')
        timestamp = data.get('timestamp')

        if not location or not timestamp:
            return jsonify({'error': 'Missing location or timestamp'}), 400

        # Get user's emergency contacts
        conn = get_db_connection()
        contacts = conn.execute('''
            SELECT * FROM emergency_contacts 
            WHERE user_id = ? 
            ORDER BY priority
        ''', (session['user_id'],)).fetchall()
        
        # Get user details
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()

        if not contacts:
            return jsonify({'error': 'No emergency contacts found'}), 400

        # Send location update to emergency contacts
        notifications_sent = 0
        for contact in contacts:
            try:
                message = f"📍 Location Update for {user['name']}:\n"
                message += f"Current Location: https://maps.google.com/?q={location['latitude']},{location['longitude']}\n"
                message += f"Time: {timestamp}\n"
                message += "This is an automated location update from HerShield."
                
                if send_sms(contact['phone'], message):
                    notifications_sent += 1
            except Exception as e:
                print(f"Error sending location update to {contact['name']}: {str(e)}")
                continue

        # Update location in database
        conn = get_alert_connection()
        conn.execute('''
            UPDATE alerts 
            SET location = ?, timestamp = ?
            WHERE user_id = ? AND status = 'active'
        ''', (
            f"{location['latitude']},{location['longitude']}",
            timestamp,
            session['user_id']
        ))
        conn.commit()
        conn.close()

        return jsonify({
            'status': 'success',
            'message': 'Location updated successfully',
            'notifications_sent': notifications_sent
        })

    except Exception as e:
        print(f"Error in update_location route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/emergency-contacts', methods=['GET', 'POST'])
def emergency_contacts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        relationship = request.form['relationship'].strip()
        priority = request.form.get('priority', 1)
        
        # Validate input
        if not name or not phone or not relationship:
            flash('All fields are required!', 'danger')
            return redirect(url_for('emergency_contacts'))
        
        # Basic phone number validation (Indian format)
        import re
        phone_pattern = re.compile(r'^(\+91|91|0)?[6-9]\d{9}$')
        if not phone_pattern.match(phone):
            flash('Please enter a valid Indian phone number!', 'danger')
            return redirect(url_for('emergency_contacts'))
        
        # Check if contact already exists
        conn = get_db_connection()
        existing = conn.execute('SELECT * FROM emergency_contacts WHERE user_id = ? AND phone = ?', 
                              (session['user_id'], phone)).fetchone()
        if existing:
            conn.close()
            flash('A contact with this phone number already exists!', 'danger')
            return redirect(url_for('emergency_contacts'))
        
        # Check maximum contacts limit (10 contacts per user)
        contact_count = conn.execute('SELECT COUNT(*) FROM emergency_contacts WHERE user_id = ?', 
                                   (session['user_id'],)).fetchone()[0]
        if contact_count >= 10:
            conn.close()
            flash('Maximum 10 emergency contacts allowed. Please delete some contacts first.', 'warning')
            return redirect(url_for('emergency_contacts'))
        
        try:
            conn.execute('INSERT INTO emergency_contacts (user_id, name, phone, relationship, priority) VALUES (?, ?, ?, ?, ?)',
                        (session['user_id'], name, phone, relationship, priority))
            conn.commit()
            flash('Emergency contact added successfully!', 'success')
        except Exception as e:
            flash('Error adding contact. Please try again.', 'danger')
            print(f"Error adding emergency contact: {e}")
        finally:
            conn.close()
        
        return redirect(url_for('emergency_contacts'))
    
    # Get user's emergency contacts
    conn = get_db_connection()
    contacts = conn.execute('SELECT * FROM emergency_contacts WHERE user_id = ? ORDER BY priority', 
                          (session['user_id'],)).fetchall()
    conn.close()
    
    # Predefined emergency numbers
    predefined_contacts = [
        {'name': 'Police', 'phone': '100', 'relationship': 'Emergency Service'},
        {'name': 'Women Helpline', 'phone': '1091', 'relationship': 'Emergency Service'},
        {'name': 'Ambulance', 'phone': '102', 'relationship': 'Emergency Service'},
        {'name': 'Fire Department', 'phone': '101', 'relationship': 'Emergency Service'},
        {'name': 'National Emergency Number', 'phone': '112', 'relationship': 'Emergency Service'}
    ]
    
    return render_template('emergency_contacts.html', contacts=contacts, predefined_contacts=predefined_contacts)

@app.route('/delete-contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM emergency_contacts WHERE id = ? AND user_id = ?', 
                    (contact_id, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Contact deleted successfully!', 'success')
    except Exception as e:
        flash('Error deleting contact. Please try again.', 'danger')
        print(f"Error deleting emergency contact: {e}")
    
    return redirect(url_for('emergency_contacts'))

@app.route('/edit-contact/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        relationship = request.form['relationship'].strip()
        priority = request.form.get('priority', 1)
        
        # Validate input
        if not name or not phone or not relationship:
            flash('All fields are required!', 'danger')
            return redirect(url_for('edit_contact', contact_id=contact_id))
        
        # Basic phone number validation (Indian format)
        import re
        phone_pattern = re.compile(r'^(\+91|91|0)?[6-9]\d{9}$')
        if not phone_pattern.match(phone):
            flash('Please enter a valid Indian phone number!', 'danger')
            return redirect(url_for('edit_contact', contact_id=contact_id))
        
        try:
            conn.execute('UPDATE emergency_contacts SET name = ?, phone = ?, relationship = ?, priority = ? WHERE id = ? AND user_id = ?',
                        (name, phone, relationship, priority, contact_id, session['user_id']))
            conn.commit()
            flash('Contact updated successfully!', 'success')
            return redirect(url_for('emergency_contacts'))
        except Exception as e:
            flash('Error updating contact. Please try again.', 'danger')
            print(f"Error updating emergency contact: {e}")
    
    # Get contact details for editing
    contact = conn.execute('SELECT * FROM emergency_contacts WHERE id = ? AND user_id = ?', 
                         (contact_id, session['user_id'])).fetchone()
    conn.close()
    
    if not contact:
        flash('Contact not found!', 'danger')
        return redirect(url_for('emergency_contacts'))
    
    return render_template('edit_contact.html', contact=contact)

@app.route('/health-tips')
def health_tips():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Health tips data
    health_tips = [
        {
            'category': 'Physical Health',
            'tips': [
                'Stay hydrated by drinking at least 8 glasses of water daily',
                'Exercise for at least 30 minutes every day',
                'Get 7-8 hours of sleep each night',
                'Maintain a balanced diet rich in fruits and vegetables',
                'Practice good posture to prevent back pain'
            ]
        },
        {
            'category': 'Mental Health',
            'tips': [
                'Practice mindfulness and meditation daily',
                'Take regular breaks from work and screens',
                'Stay connected with friends and family',
                'Keep a gratitude journal',
                'Learn stress management techniques'
            ]
        },
        {
            'category': 'Safety & Prevention',
            'tips': [
                'Carry a small first-aid kit in your bag',
                'Keep emergency contacts updated',
                'Learn basic self-defense techniques',
                'Share your location with trusted contacts when traveling',
                'Stay aware of your surroundings'
            ]
        }
    ]
    
    # Video tutorials
    video_tutorials = [
        {
            'title': 'Basic Self-Defense Techniques',
            'description': 'Learn essential self-defense moves for women',
            'url': 'https://www.youtube.com/embed/6ZpY66Xwzp8',
            'thumbnail': 'https://img.youtube.com/vi/6ZpY66Xwzp8/maxresdefault.jpg'
        },
        {
            'title': 'Women\'s Health & Wellness',
            'description': 'Comprehensive guide to women\'s health and wellness',
            'url': 'https://www.youtube.com/embed/0zBhTzHj9NU',
            'thumbnail': 'https://img.youtube.com/vi/0zBhTzHj9NU/maxresdefault.jpg'
        },
        {
            'title': 'Women\'s Self Defense - Basic Moves',
            'description': 'Simple and effective self-defense techniques',
            'url': 'https://www.youtube.com/embed/8Qn_spdM5Zg',
            'thumbnail': 'https://img.youtube.com/vi/8Qn_spdM5Zg/maxresdefault.jpg'
        },
        {
            'title': '5 Self Defense Moves Every Woman Should Know',
            'description': 'Essential self-defense techniques for women',
            'url': 'https://www.youtube.com/embed/5iPHLrAjgA8',
            'thumbnail': 'https://img.youtube.com/vi/5iPHLrAjgA8/maxresdefault.jpg'
        },
        {
            'title': 'Women\'s Health Tips',
            'description': 'Important health tips for women',
            'url': 'https://www.youtube.com/embed/2Gm6Zx5UqQY',
            'thumbnail': 'https://img.youtube.com/vi/2Gm6Zx5UqQY/maxresdefault.jpg'
        },
        {
            'title': 'Self Defense for Women - Street Safety',
            'description': 'Street safety and self-defense techniques',
            'url': 'https://www.youtube.com/embed/3N-Y36KxWfs',
            'thumbnail': 'https://img.youtube.com/vi/3N-Y36KxWfs/maxresdefault.jpg'
        },
        {
            'title': 'Women\'s Health & Fitness',
            'description': 'Health and fitness tips for women',
            'url': 'https://www.youtube.com/embed/4K5Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/4K5Y2xLhJkM/maxresdefault.jpg'
        },
        {
            'title': 'Self Defense - Ground Techniques',
            'description': 'How to defend yourself when on the ground',
            'url': 'https://www.youtube.com/embed/5L6Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/5L6Y2xLhJkM/maxresdefault.jpg'
        },
        {
            'title': 'Women\'s Mental Health',
            'description': 'Tips for maintaining mental health',
            'url': 'https://www.youtube.com/embed/6L7Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/6L7Y2xLhJkM/maxresdefault.jpg'
        },
        {
            'title': 'Self Defense with Everyday Objects',
            'description': 'Using common items for self-defense',
            'url': 'https://www.youtube.com/embed/7L8Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/7L8Y2xLhJkM/maxresdefault.jpg'
        }
    ]
    
    return render_template('health_tips.html', health_tips=health_tips, video_tutorials=video_tutorials)

@app.route('/self-defense')
def self_defense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Self-defense tips that will flash
    defense_tips = [
        "Always be aware of your surroundings",
        "Trust your instincts - if something feels wrong, it probably is",
        "Keep your phone charged and easily accessible",
        "Learn to use your voice as a weapon - yell 'FIRE!' to attract attention",
        "Carry a personal safety alarm",
        "Walk with confidence and purpose",
        "Keep your hands free and ready to defend yourself",
        "Learn basic pressure points for self-defense",
        "Practice situational awareness regularly",
        "Share your location with trusted contacts when traveling"
    ]
    
    # Self-defense video tutorials
    defense_videos = [
        {
            'title': 'Basic Self-Defense Moves for Women',
            'description': 'Essential self-defense techniques every woman should know',
            'url': 'https://www.youtube.com/embed/6ZpY66Xwzp8',
            'thumbnail': 'https://img.youtube.com/vi/6ZpY66Xwzp8/maxresdefault.jpg'
        },
        {
            'title': 'Women\'s Self-Defense Techniques',
            'description': 'Learn practical self-defense moves for women',
            'url': 'https://www.youtube.com/embed/0zBhTzHj9NU',
            'thumbnail': 'https://img.youtube.com/vi/0zBhTzHj9NU/maxresdefault.jpg'
        },
        {
            'title': 'Self Defense - Basic Techniques',
            'description': 'Fundamental self-defense moves for women',
            'url': 'https://www.youtube.com/embed/8Qn_spdM5Zg',
            'thumbnail': 'https://img.youtube.com/vi/8Qn_spdM5Zg/maxresdefault.jpg'
        },
        {
            'title': '5 Essential Self Defense Moves',
            'description': 'Must-know self-defense techniques',
            'url': 'https://www.youtube.com/embed/5iPHLrAjgA8',
            'thumbnail': 'https://img.youtube.com/vi/5iPHLrAjgA8/maxresdefault.jpg'
        },
        {
            'title': 'Street Safety & Self Defense',
            'description': 'Staying safe on the streets',
            'url': 'https://www.youtube.com/embed/3N-Y36KxWfs',
            'thumbnail': 'https://img.youtube.com/vi/3N-Y36KxWfs/maxresdefault.jpg'
        },
        {
            'title': 'Ground Defense Techniques',
            'description': 'How to defend yourself when knocked down',
            'url': 'https://www.youtube.com/embed/5L6Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/5L6Y2xLhJkM/maxresdefault.jpg'
        },
        {
            'title': 'Self Defense with Keys',
            'description': 'Using keys as a self-defense tool',
            'url': 'https://www.youtube.com/embed/6L7Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/6L7Y2xLhJkM/maxresdefault.jpg'
        },
        {
            'title': 'Mental Preparation for Self Defense',
            'description': 'Developing the right mindset',
            'url': 'https://www.youtube.com/embed/7L8Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/7L8Y2xLhJkM/maxresdefault.jpg'
        },
        {
            'title': 'Self Defense in Confined Spaces',
            'description': 'Techniques for elevators and small spaces',
            'url': 'https://www.youtube.com/embed/8L9Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/8L9Y2xLhJkM/maxresdefault.jpg'
        },
        {
            'title': 'Advanced Self Defense Combinations',
            'description': 'Combining multiple techniques effectively',
            'url': 'https://www.youtube.com/embed/9L0Y2xLhJkM',
            'thumbnail': 'https://img.youtube.com/vi/9L0Y2xLhJkM/maxresdefault.jpg'
        }
    ]
    
    return render_template('self_defense.html', defense_tips=defense_tips, defense_videos=defense_videos)

@app.route('/latest-articles')
def latest_articles():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Latest articles about women in different fields
    articles = [
        {
            'title': 'Women Breaking Barriers in Tech',
            'content': 'Women are making significant strides in technology, with more female leaders emerging in major tech companies.',
            'image': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Technology',
            'date': '2024-03-15'
        },
        {
            'title': 'Women in Sports: Record-Breaking Achievements',
            'content': 'Female athletes continue to break records and challenge stereotypes in various sports worldwide.',
            'image': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Sports',
            'date': '2024-03-14'
        },
        {
            'title': 'Women Entrepreneurs: Success Stories',
            'content': 'Women-led startups are receiving more funding and recognition in the business world.',
            'image': 'https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Business',
            'date': '2024-03-13'
        },
        {
            'title': 'Women in Science: Groundbreaking Research',
            'content': 'Female scientists are leading innovative research projects and making significant discoveries.',
            'image': 'https://images.unsplash.com/photo-1581092921461-39b9d08a9b21?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Science',
            'date': '2024-03-12'
        },
        {
            'title': 'Women in Politics: Global Leadership',
            'content': 'More women are taking leadership roles in politics and making impactful policy changes.',
            'image': 'https://images.unsplash.com/photo-1573497019230-a1d49bcfd7a9?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Politics',
            'date': '2024-03-11'
        },
        {
            'title': 'Women in Arts: Creative Excellence',
            'content': 'Female artists are gaining recognition and transforming the art world with their unique perspectives.',
            'image': 'https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Arts',
            'date': '2024-03-10'
        },
        {
            'title': 'Women in Healthcare: Medical Innovations',
            'content': 'Women healthcare professionals are pioneering new treatments and improving patient care.',
            'image': 'https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Healthcare',
            'date': '2024-03-09'
        },
        {
            'title': 'Women in Education: Shaping Future',
            'content': 'Female educators are implementing innovative teaching methods and inspiring the next generation.',
            'image': 'https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80',
            'category': 'Education',
            'date': '2024-03-08'
        }
    ]
    
    return render_template('latest_articles.html', articles=articles)

def process_markdown_response(response_text):
    """Process markdown formatting in the response for better display"""
    import re
    
    # Convert markdown to HTML for better display
    # Bold text
    response_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response_text)
    
    # Italic text
    response_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', response_text)
    
    # Bullet points
    response_text = re.sub(r'^•\s*(.*?)$', r'<li>\1</li>', response_text, flags=re.MULTILINE)
    response_text = re.sub(r'^(\d+)\.\s*(.*?)$', r'<li>\1. \2</li>', response_text, flags=re.MULTILINE)
    
    # Convert lists to proper HTML
    lines = response_text.split('\n')
    processed_lines = []
    in_list = False
    
    for line in lines:
        if line.strip().startswith('<li>'):
            if not in_list:
                processed_lines.append('<ul>')
                in_list = True
            processed_lines.append(line)
        elif in_list and not line.strip().startswith('<li>'):
            processed_lines.append('</ul>')
            in_list = False
            processed_lines.append(line)
        else:
            processed_lines.append(line)
    
    if in_list:
        processed_lines.append('</ul>')
    
    response_text = '\n'.join(processed_lines)
    
    # Convert line breaks to <br> tags
    response_text = response_text.replace('\n', '<br>')
    
    return response_text

def get_user_context(user_id=None):
    """Get user context for personalized responses"""
    if not user_id:
        return {}
    
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        contacts = conn.execute('SELECT COUNT(*) as count FROM emergency_contacts WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        
        if user:
            return {
                'name': user['name'],
                'has_emergency_contacts': contacts['count'] > 0 if contacts else False,
                'user_id': user_id
            }
    except:
        pass
    
    return {}

def save_conversation_history(user_id, user_input, ai_response, context_used=False):
    """Save conversation history to database for better context awareness"""
    if not user_id:
        return
    
    try:
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS conversation_history
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id INTEGER NOT NULL,
                         user_input TEXT NOT NULL,
                         ai_response TEXT NOT NULL,
                         context_used BOOLEAN DEFAULT FALSE,
                         timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (user_id) REFERENCES users (id))''')
        
        conn.execute('INSERT INTO conversation_history (user_id, user_input, ai_response, context_used) VALUES (?, ?, ?, ?)',
                    (user_id, user_input, ai_response, context_used))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving conversation history: {e}")

def get_conversation_history(user_id, limit=10):
    """Get recent conversation history for context"""
    if not user_id:
        return []
    
    try:
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS conversation_history
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id INTEGER NOT NULL,
                         user_input TEXT NOT NULL,
                         ai_response TEXT NOT NULL,
                         context_used BOOLEAN DEFAULT FALSE,
                         timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (user_id) REFERENCES users (id))''')
        
        history = conn.execute('''SELECT user_input, ai_response, timestamp 
                                 FROM conversation_history 
                                 WHERE user_id = ? 
                                 ORDER BY timestamp DESC 
                                 LIMIT ?''', (user_id, limit)).fetchall()
        conn.close()
        
        return [{'type': 'user', 'content': row[0], 'timestamp': row[2]} for row in history] + \
               [{'type': 'bot', 'content': row[1], 'timestamp': row[2]} for row in history]
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        user_input = request.form['user_input']
        conversation_history = request.form.get('conversation_history', '[]')
        
        try:
            # Parse conversation history
            import json
            try:
                history = json.loads(conversation_history)
            except:
                history = []
            
            # Get user context for personalization
            user_context = get_user_context(session.get('user_id'))
            
            # Get saved conversation history if user is logged in
            if user_context.get('user_id'):
                saved_history = get_conversation_history(user_context['user_id'], limit=5)
                if saved_history:
                    # Merge saved history with current session history
                    history = saved_history + history[-5:]  # Keep last 5 from current session
            
            # Create a comprehensive system prompt with conversation context
            system_prompt = f"""
            You are HerShield AI, an intelligent, empathetic, and highly responsive AI assistant designed specifically to help women with any questions, concerns, or challenges they may face. You are warm, supportive, and always prioritize safety and empowerment.

            **Your Core Expertise:**
            - Women's safety and personal security (primary focus)
            - Self-defense techniques and strategies
            - Emergency procedures and crisis management
            - Physical and mental health for women
            - Legal rights and resources (especially Indian context)
            - Personal development and empowerment
            - Relationship advice and boundaries
            - Career guidance and workplace issues
            - General life advice and support

            **Response Guidelines:**
            1. **Be Comprehensive**: Provide detailed, thorough answers that address all aspects of the question
            2. **Be Supportive**: Always maintain an empathetic and encouraging tone
            3. **Be Practical**: Offer actionable advice and concrete steps when applicable
            4. **Be Accurate**: Provide fact-based information and cite reliable sources when possible
            5. **Be Safety-Focused**: Prioritize safety in all responses, especially for emergency situations
            6. **Be Inclusive**: Consider diverse perspectives and experiences
            7. **Be Professional**: Maintain appropriate boundaries while being warm and approachable
            8. **Be Contextual**: Reference previous conversation context when relevant
            9. **Be Proactive**: Anticipate follow-up questions and provide comprehensive information
            10. **Be Encouraging**: Always end with a supportive or empowering note

            **Emergency Protocol:**
            - If someone mentions being in immediate danger, emphasize calling emergency services (100 in India)
            - Encourage using the SOS feature in the HerShield app
            - Provide clear, step-by-step emergency procedures
            - Offer immediate, actionable safety advice

            **Response Style:**
            - Use clear, accessible language
            - Include relevant emojis for warmth and visual appeal
            - Structure responses with bullet points or numbered lists when helpful
            - Provide examples and scenarios when relevant
            - Use markdown formatting for better readability
            - Keep responses conversational but informative
            - Always end with encouragement or a supportive note

            **Context Awareness:**
            - Remember previous conversation topics
            - Build on previous advice given
            - Maintain conversation continuity
            - Reference earlier points when relevant

            **Smart Features:**
            - Provide personalized advice based on context
            - Offer proactive suggestions and tips
            - Anticipate user needs and concerns
            - Provide multiple options and alternatives
            - Include relevant resources and references

            **User Context:**
            - User Name: {user_context.get('name', 'User')}
            - Has Emergency Contacts: {user_context.get('has_emergency_contacts', False)}
            - User ID: {user_context.get('user_id', 'Not logged in')}

            Now, please respond to the user's question with a comprehensive, helpful, and supportive answer that takes into account the conversation history and provides the most relevant and actionable information.
            """
            
            # Build conversation context
            context = ""
            if history:
                context = "\n\n**Conversation History:**\n"
                for i, msg in enumerate(history[-5:]):  # Last 5 messages for context
                    if msg.get('type') == 'user':
                        context += f"User: {msg.get('content', '')}\n"
                    elif msg.get('type') == 'bot':
                        context += f"Assistant: {msg.get('content', '')}\n"
            
            # Create a comprehensive prompt that includes the system context, conversation history, and user question
            full_prompt = f"{system_prompt}{context}\n\n**Current User Question:** {user_input}\n\nPlease provide a detailed, comprehensive response that addresses all aspects of this question, considers the conversation context, and offers actionable advice."
            
            try:
                # Use Gemini API for intelligent, dynamic responses
                model = genai.GenerativeModel('gemini-1.5-pro-latest')
                
                # Generate response with optimized parameters for better quality
                response = model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.9,
                        top_k=40,
                        max_output_tokens=2048,
                    )
                )
                
                # Process and enhance the response
                ai_response = response.text.strip()
                
                # Process markdown formatting
                ai_response = process_markdown_response(ai_response)
                
                # Add smart suggestions based on the response
                suggestions = generate_smart_suggestions(user_input, ai_response)
                
                # Save conversation history if user is logged in
                if user_context.get('user_id'):
                    save_conversation_history(user_context['user_id'], user_input, ai_response, len(history) > 0)
                
                # Return the enhanced response
                return jsonify({
                    'response': ai_response,
                    'suggestions': suggestions,
                    'context_used': len(history) > 0,
                    'personalized': bool(user_context.get('user_id'))
                })
                
            except Exception as e:
                print(f"Gemini API error: {str(e)}")
                # Enhanced fallback responses with better matching
                fallback_response = get_enhanced_fallback_response(user_input, history)
                fallback_response = process_markdown_response(fallback_response)
                
                # Save conversation history even for fallback responses
                if user_context.get('user_id'):
                    save_conversation_history(user_context['user_id'], user_input, fallback_response, len(history) > 0)
                
                return jsonify({'response': fallback_response})
                
        except Exception as e:
            print(f"Chatbot error: {str(e)}")
            return jsonify({'response': "I'm sorry, I'm experiencing some technical difficulties right now. Please try again in a moment, or feel free to ask me anything about safety, health, relationships, or any other topic I can help you with! 💪"})
    
    return render_template('chatbot.html')

def generate_smart_suggestions(user_input, ai_response):
    """Generate smart follow-up suggestions based on user input and AI response"""
    suggestions = []
    user_lower = user_input.lower()
    response_lower = ai_response.lower()
    
    # Emergency-related suggestions
    if any(keyword in user_lower for keyword in ['emergency', 'danger', 'help', 'sos', 'attack', 'threat', 'unsafe']):
        suggestions.extend([
            "How to use the SOS feature",
            "Emergency contact setup",
            "Self-defense techniques",
            "Safety planning tips"
        ])
    
    # Safety-related suggestions
    elif any(keyword in user_lower for keyword in ['safety', 'safe', 'protect', 'security']):
        suggestions.extend([
            "Daily safety practices",
            "Technology safety tips",
            "Travel safety guidelines",
            "Self-defense basics"
        ])
    
    # Health-related suggestions
    elif any(keyword in user_lower for keyword in ['health', 'healthy', 'wellness', 'medical', 'doctor']):
        suggestions.extend([
            "Mental health resources",
            "Physical wellness tips",
            "Preventive care guide",
            "Stress management techniques"
        ])
    
    # Relationship-related suggestions
    elif any(keyword in user_lower for keyword in ['relationship', 'dating', 'partner', 'marriage']):
        suggestions.extend([
            "Setting healthy boundaries",
            "Communication skills",
            "Red flags to watch for",
            "Building self-worth"
        ])
    
    # Career-related suggestions
    elif any(keyword in user_lower for keyword in ['career', 'job', 'work', 'profession']):
        suggestions.extend([
            "Career development tips",
            "Workplace rights",
            "Salary negotiation",
            "Professional confidence"
        ])
    
    # General suggestions based on response content
    else:
        if 'safety' in response_lower:
            suggestions.append("More safety tips")
        if 'health' in response_lower:
            suggestions.append("Health and wellness resources")
        if 'confidence' in response_lower:
            suggestions.append("Building self-confidence")
        if 'legal' in response_lower:
            suggestions.append("Legal rights and resources")
    
    # Add general helpful suggestions
    suggestions.extend([
        "Ask me anything else",
        "Emergency contacts setup",
        "Self-defense techniques"
    ])
    
    # Return unique suggestions (max 4)
    return list(dict.fromkeys(suggestions))[:4]

def get_enhanced_fallback_response(user_input, history):
    """Enhanced fallback responses with better context awareness"""
    user_lower = user_input.lower()
    
    # Enhanced fallback responses for when API fails
    fallback_responses = {
        'emergency': "🚨 **EMERGENCY RESPONSE** 🚨\n\nIf you're in immediate danger:\n\n1. **Call 100 immediately** - Police emergency number\n2. **Use the SOS button** in this app to alert your emergency contacts\n3. **Find a safe location** - Go to a well-lit, public area\n4. **Stay visible** - Make yourself seen by others\n5. **Trust your instincts** - If something feels wrong, act on it\n\n**Remember**: Your safety is the absolute priority. Don't hesitate to call for help.\n\n💪 You're stronger than you think, and help is always available.",
        
        'safety': "🛡️ **COMPREHENSIVE SAFETY GUIDELINES** 🛡️\n\n**Daily Safety Practices:**\n• Trust your instincts - if something feels wrong, it probably is\n• Stay aware of your surroundings at all times\n• Keep your phone charged and easily accessible\n• Share your location with trusted contacts when traveling\n• Carry a personal safety alarm or whistle\n• Learn basic self-defense techniques\n\n**Technology Safety:**\n• Use location-sharing apps with trusted friends\n• Keep emergency contacts updated\n• Consider safety apps like HerShield\n• Be cautious with social media location sharing\n\n**Mental Safety:**\n• Build confidence through self-care\n• Practice situational awareness\n• Develop a safety mindset\n• Trust your judgment\n\n💪 Remember: You have the right to feel safe and secure.",
        
        'self defense': "🥋 **SELF-DEFENSE COMPREHENSIVE GUIDE** 🥋\n\n**Mental Preparation:**\n• Develop situational awareness\n• Trust your instincts\n• Stay calm under pressure\n• Be mentally prepared to defend yourself\n\n**Basic Techniques:**\n• **Voice as weapon**: Yell 'FIRE!' to attract attention\n• **Target vulnerable areas**: Eyes, nose, throat, groin\n• **Use your body**: Elbows, knees, head for striking\n• **Create distance**: Push, kick, or run when possible\n\n**Prevention Strategies:**\n• Avoid isolated areas\n• Walk with confidence\n• Keep hands free and ready\n• Learn pressure points\n• Practice basic moves regularly\n\n**Training Recommendations:**\n• Take a self-defense class\n• Practice with a partner\n• Learn martial arts basics\n• Attend women's safety workshops\n\n💪 Knowledge is power - the more you know, the safer you are!",
        
        'health': "💪 **WOMEN'S HEALTH & WELLNESS GUIDE** 💪\n\n**Physical Health:**\n• Regular health checkups and screenings\n• Balanced nutrition with adequate vitamins\n• Regular exercise (30+ minutes daily)\n• Adequate sleep (7-9 hours)\n• Stay hydrated (8+ glasses of water)\n\n**Mental Health:**\n• Practice mindfulness and meditation\n• Maintain social connections\n• Seek professional help when needed\n• Practice stress management techniques\n• Set healthy boundaries\n\n**Preventive Care:**\n• Annual gynecological exams\n• Breast self-examinations\n• Bone density screenings\n• Mental health check-ins\n• Regular dental care\n\n**Lifestyle Tips:**\n• Limit alcohol and avoid smoking\n• Practice safe sex\n• Manage stress effectively\n• Prioritize self-care\n• Build a support network\n\n💪 Your health is your foundation - invest in it daily!",
        
        'confidence': "💎 **BUILDING UNSTOPPABLE CONFIDENCE** 💎\n\n**Self-Care Foundation:**\n• Practice daily self-love and acceptance\n• Celebrate small wins and achievements\n• Take care of your physical appearance\n• Maintain good posture and body language\n\n**Mental Strength:**\n• Challenge negative self-talk\n• Practice positive affirmations\n• Set and achieve small goals\n• Learn from failures and setbacks\n• Develop a growth mindset\n\n**Social Confidence:**\n• Practice speaking up in safe environments\n• Set and maintain healthy boundaries\n• Surround yourself with supportive people\n• Learn to say 'no' without guilt\n• Express your opinions respectfully\n\n**Professional Confidence:**\n• Develop your skills and expertise\n• Take on new challenges\n• Advocate for yourself at work\n• Build a professional network\n• Ask for what you deserve\n\n**Daily Practices:**\n• Power posing for 2 minutes daily\n• Gratitude journaling\n• Visualization exercises\n• Positive self-talk\n• Regular exercise\n\n💎 Confidence is a skill you can develop - start today!",
        
        'mental': "🧠 **MENTAL HEALTH & WELLNESS COMPREHENSIVE GUIDE** 🧠\n\n**Understanding Mental Health:**\n• Mental health is as important as physical health\n• It's okay to not be okay sometimes\n• Seeking help is a sign of strength, not weakness\n• Everyone experiences mental health challenges\n\n**Daily Wellness Practices:**\n• **Mindfulness**: Practice meditation or deep breathing\n• **Gratitude**: Keep a gratitude journal\n• **Movement**: Exercise releases endorphins\n• **Connection**: Maintain meaningful relationships\n• **Sleep**: Prioritize quality sleep\n• **Nutrition**: Eat brain-healthy foods\n\n**Stress Management:**\n• Identify your stress triggers\n• Practice time management\n• Learn to delegate tasks\n• Take regular breaks\n• Use relaxation techniques\n• Set realistic expectations\n\n**When to Seek Help:**\n• Persistent sadness or anxiety\n• Changes in sleep or appetite\n• Difficulty concentrating\n• Withdrawal from activities\n• Thoughts of self-harm\n• Feeling overwhelmed\n\n**Professional Support:**\n• Therapists and counselors\n• Psychiatrists for medication\n• Support groups\n• Crisis hotlines\n• Online therapy platforms\n\n🧠 Remember: Your mental health matters, and you deserve support!",
        
        'legal': "⚖️ **WOMEN'S LEGAL RIGHTS & RESOURCES** ⚖️\n\n**Key Legal Protections in India:**\n• **Protection of Women from Domestic Violence Act, 2005**\n• **Sexual Harassment of Women at Workplace Act, 2013**\n• **Maternity Benefit Act, 1961**\n• **Equal Remuneration Act, 1976**\n• **Dowry Prohibition Act, 1961**\n\n**Your Rights Include:**\n• Right to live free from violence and harassment\n• Right to equal pay for equal work\n• Right to maternity benefits\n• Right to file complaints without fear\n• Right to legal aid and support\n\n**Emergency Contacts:**\n• **Women Helpline**: 1091\n• **Domestic Violence Helpline**: 181\n• **Police Emergency**: 100\n• **Child Helpline**: 1098\n\n**Legal Resources:**\n• National Commission for Women\n• State Women Commissions\n• Legal Aid Services\n• Women's Rights Organizations\n• Pro Bono Legal Services\n\n**Steps to Take:**\n• Document incidents with dates and details\n• Keep evidence (photos, messages, medical reports)\n• File complaints with appropriate authorities\n• Seek legal counsel when needed\n• Connect with support groups\n\n⚖️ Knowledge of your rights is your first line of defense!",
        
        'transport': "🚌 **PUBLIC TRANSPORT SAFETY COMPREHENSIVE GUIDE** 🚌\n\n**Before Traveling:**\n• Plan your route in advance\n• Share your travel plans with trusted contacts\n• Keep emergency contacts easily accessible\n• Charge your phone fully\n• Carry a personal safety alarm\n\n**While Traveling:**\n• Stay alert and aware of surroundings\n• Keep belongings close and secure\n• Sit near other women when possible\n• Avoid isolated areas of transport\n• Trust your instincts about people\n\n**Safety Strategies:**\n• **Bus Safety**: Sit near the driver or conductor\n• **Train Safety**: Choose women's compartments when available\n• **Metro Safety**: Stay in well-lit areas\n• **Auto/Taxi Safety**: Share ride details with contacts\n• **Walking**: Stay in well-lit, populated areas\n\n**Technology Safety:**\n• Use ride-sharing apps with safety features\n• Share live location with trusted contacts\n• Keep emergency apps ready\n• Use women-only transport options when available\n\n**Emergency Response:**\n• Know emergency numbers by heart\n• Use panic buttons on transport apps\n• Alert authorities if you feel unsafe\n• Exit at the next stop if uncomfortable\n• Call for help immediately if threatened\n\n🚌 Stay safe, stay alert, and trust your instincts!",
        
        'relationship': "💕 **HEALTHY RELATIONSHIPS & BOUNDARIES** 💕\n\n**Building Healthy Relationships:**\n• **Communication**: Open, honest, and respectful dialogue\n• **Trust**: Foundation of any strong relationship\n• **Respect**: Mutual respect for boundaries and feelings\n• **Support**: Emotional and practical support for each other\n• **Equality**: Balanced power dynamics\n\n**Setting Boundaries:**\n• **Identify your limits**: Know what you're comfortable with\n• **Communicate clearly**: Express boundaries respectfully\n• **Be consistent**: Maintain boundaries consistently\n• **Respect others**: Honor others' boundaries too\n• **Self-care**: Prioritize your well-being\n\n**Red Flags to Watch For:**\n• Controlling behavior or jealousy\n• Disrespect for your boundaries\n• Emotional or physical abuse\n• Isolation from friends and family\n• Financial control or manipulation\n• Gaslighting or manipulation\n\n**Building Self-Worth:**\n• Practice self-love and acceptance\n• Develop independence and interests\n• Maintain your own friendships\n• Pursue your goals and dreams\n• Don't compromise your values\n\n**Seeking Help:**\n• Talk to trusted friends or family\n• Consider professional counseling\n• Contact domestic violence hotlines\n• Join support groups\n• Prioritize your safety\n\n💕 You deserve relationships that lift you up, not bring you down!",
        
        'career': "💼 **WOMEN'S CAREER DEVELOPMENT & EMPOWERMENT** 💼\n\n**Career Planning:**\n• **Self-Assessment**: Identify your strengths and interests\n• **Goal Setting**: Set clear, achievable career goals\n• **Skill Development**: Continuously upgrade your skills\n• **Networking**: Build professional relationships\n• **Mentorship**: Seek guidance from experienced professionals\n\n**Overcoming Challenges:**\n• **Gender Bias**: Address bias professionally and assertively\n• **Work-Life Balance**: Set boundaries and prioritize effectively\n• **Imposter Syndrome**: Recognize your achievements and worth\n• **Salary Negotiation**: Research and advocate for fair compensation\n• **Leadership**: Develop leadership skills and confidence\n\n**Professional Development:**\n• **Continuous Learning**: Stay updated with industry trends\n• **Certifications**: Pursue relevant certifications\n• **Public Speaking**: Develop communication skills\n• **Leadership Training**: Take on leadership opportunities\n• **Mentoring Others**: Share your knowledge and experience\n\n**Workplace Rights:**\n• **Equal Pay**: Advocate for fair compensation\n• **Safe Environment**: Report harassment and discrimination\n• **Maternity Benefits**: Know your rights and benefits\n• **Flexible Work**: Request reasonable accommodations\n• **Professional Growth**: Seek advancement opportunities\n\n**Building Confidence:**\n• **Celebrate Achievements**: Acknowledge your successes\n• **Take Risks**: Step out of your comfort zone\n• **Learn from Failures**: View setbacks as learning opportunities\n• **Self-Advocacy**: Speak up for yourself professionally\n• **Support Network**: Build relationships with other professionals\n\n💼 Your career is your journey - own it with confidence and purpose!"
    }
    
    # Check for emergency keywords first
    emergency_keywords = ['emergency', 'danger', 'help', 'sos', 'attack', 'threat', 'unsafe', 'scared', 'fear']
    if any(keyword in user_lower for keyword in emergency_keywords):
        return fallback_responses['emergency']
    
    # Check for other categories with enhanced matching
    category_keywords = {
        'safety': ['safety', 'safe', 'protect', 'security', 'secure', 'dangerous', 'unsafe'],
        'self defense': ['self defense', 'self-defense', 'defend', 'fight', 'protect', 'martial arts', 'attack'],
        'health': ['health', 'healthy', 'wellness', 'medical', 'doctor', 'exercise', 'diet', 'sick', 'pain'],
        'confidence': ['confidence', 'confident', 'self-esteem', 'self worth', 'empowerment', 'shy', 'nervous'],
        'mental': ['mental health', 'mental', 'anxiety', 'depression', 'stress', 'therapy', 'sad', 'worried'],
        'legal': ['legal', 'rights', 'law', 'lawyer', 'court', 'harassment', 'discrimination', 'abuse'],
        'transport': ['transport', 'bus', 'train', 'metro', 'travel', 'commute', 'public transport', 'traveling'],
        'relationship': ['relationship', 'dating', 'marriage', 'partner', 'boyfriend', 'girlfriend', 'love', 'breakup'],
        'career': ['career', 'job', 'work', 'profession', 'business', 'employment', 'salary', 'promotion']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            return fallback_responses.get(category, fallback_responses['safety'])
    
    # If no specific category matches, provide a general supportive response
    return "I'm here to help you with any questions or concerns you might have! Whether it's about safety, health, relationships, career, or anything else, I'm ready to provide detailed, supportive guidance. Please feel free to ask me anything - no question is too big or too small. 💪\n\n**Some topics I can help with:**\n• Safety and self-defense\n• Physical and mental health\n• Relationships and boundaries\n• Career development\n• Legal rights and resources\n• Personal growth and confidence\n• Emergency procedures\n• And much more!"

if __name__ == '__main__':
    app.run(debug=True)
