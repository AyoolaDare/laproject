# /api/index.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re
import os
import logging
import traceback

# --- Flask App Definition for Vercel ---
app = Flask(__name__)
CORS(app)

# Configure basic logging for debugging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

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
    required_fields = ['first-name', 'last-name', 'email', 'phone', 'address', 'city-state', 'zipcode', 'gender', 'age', 'bank-name']
    for field in required_fields:
        # protect against None data
        value = None if data is None else data.get(field)
        if not value or not str(value).strip():
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
        app.logger.error("Failed to parse JSON body:\n%s", traceback.format_exc())
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400

    # If no JSON body was provided, tell the client
    if data is None:
        app.logger.info("No JSON body received in request to /sendmail")
        return jsonify({"status": "error", "message": "No JSON body provided. Ensure Content-Type: application/json and that you send a JSON payload."}), 400

    validation_errors = validate_form_data(data)
    if validation_errors:
        return jsonify({"status": "error", "message": " | ".join(validation_errors)}), 400

    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        # Log which env vars are missing (but never log the password value)
        app.logger.error("Email env vars missing. SENDER_EMAIL set: %s, RECEIVER_EMAIL set: %s, SENDER_PASSWORD set: %s",
                         bool(SENDER_EMAIL), bool(RECEIVER_EMAIL), bool(SENDER_PASSWORD))
        return jsonify({"status": "error", "message": "Server is not configured to send emails. Missing environment variables."}), 500

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
Bank Name: {data.get('bank-name', 'N/A')}"""
        
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attempt to send email and provide clearer logs for common SMTP failures
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as server:
            server.set_debuglevel(0)
            server.starttls()
            try:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
            except smtplib.SMTPAuthenticationError as auth_err:
                app.logger.error("SMTP authentication failed: %s", auth_err)
                app.logger.debug(traceback.format_exc())
                return jsonify({"status": "error", "message": "SMTP authentication failed. Check SENDER_EMAIL and SENDER_PASSWORD (use an app password if using Gmail with 2FA)."}), 500
            except Exception as e:
                app.logger.error("Unexpected error during SMTP login: %s", e)
                app.logger.debug(traceback.format_exc())
                return jsonify({"status": "error", "message": "Failed to login to SMTP server."}), 500

            try:
                server.send_message(msg)
            except Exception as send_err:
                app.logger.error("Failed to send email: %s", send_err)
                app.logger.debug(traceback.format_exc())
                return jsonify({"status": "error", "message": "Failed to send email. See server logs for details."}), 500

        return jsonify({"status": "success", "message": "Form sent successfully!", "redirect": "/thank_you.html"}), 200

    except Exception as e:
        # Log full traceback to server logs for debugging; return a safe message to client
        app.logger.error("---!!! PRODUCTION EMAIL SENDING FAILED: %s !!!---", e)
        app.logger.debug(traceback.format_exc())
        return jsonify({"status": "error", "message": "An internal error occurred. See server logs for details."}), 500


# Helpful local-run guard for testing (ignored on platforms like Vercel)
if __name__ == '__main__':
    # For local testing: ensure logs are verbose
    app.logger.setLevel(logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    app.run(host='0.0.0.0', port=5000, debug=True)