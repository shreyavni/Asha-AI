

# --- Existing Imports ---
# --- Existing Imports ---
import logging
from flask import Flask, request, render_template, redirect, url_for, session, flash, get_flashed_messages, jsonify
from assistant import chatbot_logic  # Assuming assistant is a package and chatbot_logic is a module
from flask_mail import Mail, Message
from datetime import datetime
import config
import os
# import json # Might be needed for debugging prints
# import json # Might be needed for debugging prints

# --- New Imports for Authentication ---
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
# --- Import for Google OAuth ---
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv  # To load .env file for credentials
from flask_migrate import Migrate 
# --- Load .env file (if you use it) ---
load_dotenv()

# --- Existing Flask App Initialization ---
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Load Secret Key from Config/Env ---
app.secret_key = os.getenv("FLASK_SECRET_KEY", config.FLASK_SECRET_KEY)  # Prioritize .env
if not app.secret_key:
    print("FATAL: FLASK_SECRET_KEY is not set in config.py or .env.")
    exit()

# --- SQLAlchemy Setup ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI", config.SQLALCHEMY_DATABASE_URI)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class ContactSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        # __repr__ is helpful for debugging
        return f"<ContactSubmission id={self.id} name='{self.name}' email='{self.email}'>"

# --- Email Configuration (Flask-Mail) ---
# IMPORTANT: Replace with your actual SMTP server details and credentials.
# Using environment variables is highly recommended for credentials in production!
app.config['MAIL_SERVER'] = 'smtp.example.com' # e.g., 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587 # or 465 for SSL
app.config['MAIL_USE_TLS'] = True # Set to False if using SSL (port 465)
app.config['MAIL_USE_SSL'] = False # Set to True if using SSL (port 465)
app.config['MAIL_USERNAME'] = 'your_email@example.com' # Your sending email address
app.config['MAIL_PASSWORD'] = 'your_email_password' # Your email password
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@example.com' # Sender display email
MAIL_RECIPIENT = 'your_admin_email@example.com' # The email address submissions go to

mail = Mail(app)

# --- Dummy data or simulation for demonstration (Same as before) ---
class DummyUser:
    def __init__(self, username, name=None, profile_pic=None):
        self.username = username
        self.name = name
        self.profile_pic = profile_pic # Path relative to static, e.g., 'images/user1.jpg'

# Simulate a logged-in user for the index page for demonstration
SIMULATED_USER = DummyUser(username='testuser', name='Test User', profile_pic='images/default_profile.png')
# SIMULATED_USER = None # Uncomment this to simulate a guest user


migrate = Migrate(app, db)
# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect here if @login_required fails
login_manager.login_message_category = 'info'

# --- Google OAuth Setup ---
# Load Google credentials (prioritize .env, fallback to config.py)
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', getattr(config, 'GOOGLE_CLIENT_ID', None))
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', getattr(config, 'GOOGLE_CLIENT_SECRET', None))
app.config['GOOGLE_SERVER_METADATA_URL'] = 'https://accounts.google.com/.well-known/openid-configuration'

if not app.config['GOOGLE_CLIENT_ID'] or not app.config['GOOGLE_CLIENT_SECRET']:
    print("WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured. Google OAuth will not work.")
    oauth = None  # Disable OAuth if keys are missing
else:
    oauth = OAuth(app)
    oauth.register(
        name='google',
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url=app.config.get("GOOGLE_SERVER_METADATA_URL"),
        client_kwargs={
            'scope': 'openid email profile'  # Request necessary user info (profile includes name and picture)
        }
    )


# --- Modified User Model ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Make username unique but consider if it's always required (e.g., for Google-only users)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Password hash is now nullable for users who sign up via OAuth
    password_hash = db.Column(db.String(128), nullable=True)
    # --- NEW: Store Google's unique ID ---
    google_id = db.Column(db.String(120), unique=True, nullable=True)
    # Add other fields as before
    # --- UNCOMMENTED: Store name and profile picture URL from Google ---
    name = db.Column(db.String(100), nullable=True) # Example: Store name from Google
    profile_pic = db.Column(db.String(200), nullable=True) # Example: Store pic URL

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        # Ensure password_hash is not None before checking
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# --- User loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        # Ensure user_id is an integer before querying
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None  # Invalid user_id format
    return None


# --- Existing Route: Home Page (Modified Redirect) ---
@app.route('/')
def home():
    return render_template('home.html', user=current_user)
@app.route('/chatapp')
def index():
    """Serves the main chat page. Redirects to login if not authenticated."""
    if not current_user.is_authenticated:
        flash('Please log in to use the chat.', 'info')
        # Redirect to LOGIN page, which offers both local and Google login
        return redirect(url_for('login'))

    # Initialize or validate chat history
    if 'chat_history' not in session or not isinstance(session.get('chat_history'), list):
        session['chat_history'] = []
        # Optionally print only during debug or development
        # print("Initialized/Corrected chat history in session.")

    # Pass user information if needed by the template
    return render_template('index.html', user=current_user)


# --- Existing Route: Chat Endpoint ---
@app.route('/chat', methods=['POST'])
@login_required  # Protect the chat endpoint
def chat():
    """Handles chatbot requests, managing history via session."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "Missing 'message' key"}), 400

    chat_history = session.get('chat_history', [])
    if not isinstance(chat_history, list):
        print(f"Warning: Invalid chat_history type in session ({type(chat_history)}), resetting.")
        chat_history = []

    # Process message
    response_message, suggestions, updated_history = chatbot_logic.process_message(
        user_input=user_message,
        chat_history=chat_history
    )

    session['chat_history'] = updated_history
    session.modified = True

    return jsonify({
        "response": response_message,
        "suggestions": suggestions
    })


# --- Existing Route: Clear History ---
@app.route('/clear_history', methods=['POST'])
@login_required  # Should require login to clear history associated with the session
def clear_history():
    """Endpoint to clear the chat history from the session."""
    session.pop('chat_history', None)
    print("Chat history cleared.")
    return jsonify({"status": "History cleared"})


# --- New Route: User Registration ---
@app.route('/register', methods=['POST'])
def register():
    """Handles local user registration."""
    if current_user.is_authenticated:
        flash('You are already registered and logged in.', 'info')
        return redirect(url_for('index'))  # Redirect to index/profile

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('login',reg=True))

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash('Username or email already exists. Please log in or choose different details.', 'warning')
            return redirect(url_for('login',reg=True))

        new_user = User(username=username, email=email)
        new_user.set_password(password)  # Hash the password

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during registration: {e}', 'danger')
            print(f"Database error during registration: {e}")
            return redirect(url_for('login',reg=True))

    # Pass oauth status to template to conditionally show Google button
    return render_template('register.html', title='Register', oauth_enabled=bool(oauth))


# --- New Route: User Login (Local) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles local user login."""
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('index'))  # Or profile

    if request.method == 'POST':
        username = request.form.get('username')  # Or allow login via email
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        # Allow login by username OR email
        user = User.query.filter((User.username == username) | (User.email == username)).first()

        # Check if user exists and the password is correct (and password exists)
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            # Redirect to next page or index
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username/email or password.', 'danger')
            return redirect(url_for('login'))

    # Pass oauth status to template to conditionally show Google button
    return render_template('login.html', title='Login', oauth_enabled=bool(oauth))


# --- New Route: Google Login Initiator ---
@app.route('/google/login')
def google_login():
    """Initiates the Google OAuth flow."""
    if not oauth:  # Check if OAuth was initialized
        flash('Google OAuth is not configured correctly.', 'danger')
        return redirect(url_for('login'))

    # Store the nonce in the session
    nonce = os.urandom(16).hex()  # Generate a random nonce
    session['google_oauth_nonce'] = nonce

    # Define the callback URL for Google redirect
    # Must match EXACTLY one of the URIs in Google Cloud Console Credentials
    redirect_uri = url_for('google_authorize', _external=True)
    print(f"DEBUG: Redirect URI for Google: {redirect_uri}")  # For debugging
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)  # Pass the nonce


# --- New Route: Google OAuth Callback ---
@app.route('/google/authorize')
def google_authorize():
    """Handles the callback from Google after authentication."""
    if not oauth:
        flash('Google OAuth is not configured correctly.', 'danger')
        return redirect(url_for('login'))

    try:
        # Exchange authorization code for tokens
        token = oauth.google.authorize_access_token()
        # Get the nonce from the session
        nonce = session.pop('google_oauth_nonce', None)
        if not nonce:
            flash('Nonce not found in session.  Possible security issue.', 'danger')
            return redirect(url_for('login'))

        # Parse user info from the ID token (contains sub, email, name, picture, etc.)
        user_info = oauth.google.parse_id_token(token, nonce=nonce)  # Pass the nonce

        google_id = user_info.get('sub')  # Google's unique ID for the user
        email = user_info.get('email')
        name = user_info.get('name') # Get the user's name from Google
        picture = user_info.get('picture') # Get the profile picture URL from Google

        if not email or not google_id:
            flash('Failed to get necessary information from Google. Please ensure email permission is granted.', 'danger')
            return redirect(url_for('login'))

        # --- Find or Create User ---
        user = User.query.filter_by(google_id=google_id).first()

        if user is None:
            # User not found by google_id, try finding by email
            user = User.query.filter_by(email=email).first()
            if user:
                # Found by email, link their Google ID and update profile info
                user.google_id = google_id
                user.name = name # Update name
                user.profile_pic = picture # Update profile picture URL
                db.session.commit()
                print(f"Linked existing user {user.username} (Email: {email}) with Google ID.")
            else:
                # User not found by email either, create a new user
                # Generate a unique username (handle potential collisions)
                username_base = email.split('@')[0].replace('.', '').replace('+', '')  # Basic sanitization
                username = username_base
                counter = 1
                # Keep trying usernames until a unique one is found
                while User.query.filter_by(username=username).first():
                    username = f"{username_base}_{counter}"
                    counter += 1
                    if counter > 100:  # Safety break
                        flash('Could not generate a unique username. Please register manually.', 'danger')
                        return redirect(url_for('login', reg=True))

                print(f"Creating new user via Google: Email={email}, Username={username}")
                user = User(
                    google_id=google_id,
                    email=email,
                    username=username,  # Use generated username
                    name=name, # Store name from Google
                    profile_pic=picture # Store profile picture URL from Google
                    # password_hash is None by default (nullable=True)
                )
                db.session.add(user)
                try:
                    db.session.commit()
                except Exception as e_commit:
                    db.session.rollback()
                    print(f"Error saving new Google user: {e_commit}")
                    flash('Error creating your account from Google profile.', 'danger')
                    return redirect(url_for('login'))

        # --- Log the user in using Flask-Login ---
        login_user(user)  # Flask-Login handles the session
        flash('Logged in successfully via Google!', 'success')

        # Redirect to the intended page or index
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    except Exception as e:
        # Catch potential errors during token exchange or user info parsing
        print(f"Error during Google authorization: {e}")
        flash(f'Google login failed. Error: {str(e)}', 'danger')
        return redirect(url_for('login'))


# --- Existing Route: User Logout ---
@app.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    logout_user()  # Clears user session via Flask-Login
    session.pop('chat_history', None)  # Also clear chat history on logout
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))  # Redirect to login page


# --- Existing Route: User Profile View ---
@app.route('/profile')
@login_required
def profile():
    """Displays the current user's profile."""
    return render_template('profile.html', title='Profile', user=current_user)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """
    Handles displaying the contact form (GET) and processing submissions (POST).
    Includes validation, database saving, email sending, and logging.
    """
    if request.method == 'POST':
        # Get data from the submitted form
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        logging.info(f"Attempting to process contact form submission from {email}")

        # --- 1. Validate the data ---
        errors = []
        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        elif '@' not in email or '.' not in email: # Basic email format check
             errors.append('Invalid email format.')
        if not message:
            errors.append('Message is required.')

        if errors:
            # If validation fails, flash error messages and redirect back
            for error in errors:
                flash(error, 'danger') # 'danger' is a category for styling
            logging.warning(f"Validation failed for submission from {email}: {errors}")
            # It's often better to re-render the form with errors and input
            # return render_template('contact.html', errors=errors, name=name, email=email, phone=phone, message=message)
            return redirect(url_for('contact')) # Redirecting for simplicity here

        # --- 2. Save to a database ---
        try:
            new_submission = ContactSubmission(
                name=name,
                email=email,
                phone=phone,
                message=message
            )
            db.session.add(new_submission)
            db.session.commit()
            logging.info(f"Successfully saved submission from {email} to database.")
        except Exception as e:
            db.session.rollback() # Rollback the transaction on error
            logging.error(f"Database error saving submission from {email}: {e}")
            flash('An error occurred while saving your submission.', 'danger')
            return redirect(url_for('contact'))

        # --- 3. Send an email ---
        try:
            msg = Message('New Contact Form Submission',
                          sender=app.config['MAIL_DEFAULT_SENDER'],
                          recipients=[MAIL_RECIPIENT]) # Send email to admin
            msg.body = f"""
New contact form submission received:

Name: {name}
Email: {email}
Phone: {phone if phone else 'N/A'}

Message:
{message}
"""
            mail.send(msg)
            logging.info(f"Successfully sent contact email for submission from {email}.")
        except Exception as e:
            # Log the email sending error but don't necessarily fail the whole request
            logging.error(f"Error sending email for submission from {email}: {e}")
            # You might want to add a flash message about email sending failure too
            # flash('Could not send confirmation email.', 'warning') # Optional

        # --- 4. Log the successful submission ---
        # We already logged success for database and email separately.
        # A final success log:
        logging.info(f"Contact form submission processed successfully from {email}.")

        # --- Provide Feedback and Redirect ---
        flash('Your message has been sent successfully!', 'success') # 'success' is a category
        return redirect(url_for('contact')) # Redirect back to the contact page

    # If it's a GET request, render the contact form page
    # You can optionally pass flash messages to the template if you display them manually
    return render_template('contact.html')

# --- Existing Route: User Profile Edit ---
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Handles editing the current user's profile."""
    user = current_user

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_password = request.form.get('new_password')  # Optional password change

        # --- Validation ---
        # Check if username or email is being changed to one that already exists (and isn't the current user's)
        if new_username != user.username and User.query.filter_by(username=new_username).first():
            flash('Username already taken. Please choose another.', 'warning')
            return render_template('edit_profile.html', title='Edit Profile', user=user)
        if new_email != user.email and User.query.filter_by(email=new_email).first():
            flash('Email address already registered. Please choose another.', 'warning')
            return render_template('edit_profile.html', title='Edit Profile', user=user)

        # Update user details
        user.username = new_username
        user.email = new_email
        # user.first_name = request.form.get('first_name') # If you have these fields

        # Handle password change only if a new password was provided
        if new_password:
            # You might want to add a "current password" check here for security
            user.set_password(new_password)
            flash('Password updated successfully.', 'info')

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating your profile: {e}', 'danger')
            print(f"Database error during profile update: {e}")
            # Stay on edit page

    # Render the edit form with current user data
    return render_template('edit_profile.html', title='Edit Profile', user=user)


# --- Run the Flask app ---
if __name__ == '__main__':
    with app.app_context():
        print("Checking/Creating database tables...")
        # This will create tables based on the LATEST models, including the new 'google_id' field
        # and the nullable 'password_hash'.
        # WARNING: If the table structure changed drastically and you have existing data,
        # this might fail or lead to data loss. Use Flask-Migrate for production.
        try:
            db.create_all()
            print("Database tables checked/created successfully.")
        except Exception as e:
            print(f"ERROR: Could not create database tables: {e}")
            print("Please check your database connection string and permissions.")
            exit(1)  # Exit if database setup fails

    print("Starting Flask development server...")
    # Use threaded=True if your chatbot logic might block, but be mindful of thread safety
    app.run(debug=True, host='127.0.0.1', port=10000, threaded=True)
