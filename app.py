"""
Menke Vacca Wedding Website
A Flask web application for wedding RSVP and registry management
"""

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_mail import Mail, Message
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import logging
from dotenv import load_dotenv

# Try to import Azure Communication Services (optional)
try:
    from azure.communication.email import EmailClient
    AZURE_EMAIL_AVAILABLE = True
except ImportError:
    AZURE_EMAIL_AVAILABLE = False
    print("Azure Communication Services not available. Using SMTP fallback.")

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Determine if we should use local SMTP server
use_local_smtp = (
    os.environ.get('FLASK_ENV') == 'development' and 
    not os.environ.get('MAIL_USERNAME')
)

# Configuration
if use_local_smtp:
    # Development configuration with local SMTP server
    app.config.update(
        MAIL_SERVER='localhost',
        MAIL_PORT=1025,
        MAIL_USE_TLS=False,
        MAIL_USE_SSL=False,
        MAIL_USERNAME=None,
        MAIL_PASSWORD=None,
        MAIL_DEFAULT_SENDER='dev@menkevaccawedding.com',
        MAIL_SUPPRESS_SEND=False
    )
    print("📧 Using local SMTP server for development")
else:
    # Production configuration - supports multiple email providers
    mail_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = int(os.environ.get('MAIL_PORT', 587))
    mail_use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    
    app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME')),
        MAIL_SUPPRESS_SEND=False if os.environ.get('MAIL_USERNAME') else True
    )
    
    # Log which email provider is being used
    if 'sendgrid' in mail_server:
        print(f"📧 Using SendGrid SMTP")
    elif 'gmail' in mail_server:
        print(f"📧 Using Gmail SMTP with {os.environ.get('MAIL_USERNAME')}")
    else:
        print(f"📧 Using custom SMTP server: {mail_server}:{mail_port}")
    
    if not os.environ.get('MAIL_USERNAME'):
        print("⚠️  Email not configured - emails will not be sent")

# Initialize Flask-Mail
mail = Mail(app)

# Google Sheets configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1VKJ3ZPchlJ1CFpRgBygx0HnwO5nDZUnwHouZSsRLDlE'

def get_google_sheets_client():
    """Initialize Google Sheets client with service account credentials"""
    
    try:
        # Load credentials from environment variable
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDS_JSON')
        print(os.environ.get('FLASK_ENV'))
        print(os.environ.get('GOOGLE_SHEETS_CREDS_JSON'))
        # Debug logging
        app.logger.info(f"🔍 GOOGLE_SHEETS_CREDS_JSON exists: {creds_json is not None}")
        if creds_json:
            app.logger.info(f"🔍 JSON length: {len(creds_json)} characters")
            app.logger.info(f"🔍 JSON starts with: {creds_json[:100]}...")
        else:
            app.logger.error("❌ GOOGLE_SHEETS_CREDS_JSON environment variable not set")
            # List all environment variables for debugging
            env_vars = [key for key in os.environ.keys() if 'GOOGLE' in key.upper()]
            app.logger.error(f"🔍 Available env vars with 'GOOGLE': {env_vars}")
            return None
        
        # Parse JSON credentials
        app.logger.info("🔍 Attempting to parse JSON...")
        creds_info = json.loads(creds_json)
        app.logger.info("✅ JSON parsed successfully")
        
        credentials = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(credentials)
        app.logger.info("✅ Google Sheets client created successfully")
        return client
    except json.JSONDecodeError as e:
        app.logger.error(f"❌ JSON decode error: {e}")
        app.logger.error(f"🔍 Problematic JSON: {creds_json}")
        return None
    except Exception as e:
        app.logger.error(f"❌ Error initializing Google Sheets client: {e}")
        return None

def scrape_title_from_url(url):
    """Scrape title from product URL if title is missing"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try multiple selectors for title
        title_selectors = [
            'h1',
            '.product-title',
            '[data-testid="product-title"]',
            '.pdp-product-name',
            'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        return "Product"  # Fallback title
    except Exception as e:
        app.logger.warning(f"Could not scrape title from {url}: {e}")
        return "Product"

@app.route('/')
def home():
    """Home page with wedding information"""
    return render_template('home.html')

@app.route('/rsvp')
def rsvp():
    """RSVP page - to be configured later"""
    return render_template('rsvp.html')

@app.route('/registry')
def registry():
    """Registry page displaying items from Google Sheets"""
    try:
        client = get_google_sheets_client()
        if not client:
            flash('Unable to load registry at this time. Please try again later.', 'error')
            return render_template('registry.html', items=[])
        
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        records = sheet.get_all_records()
        
        # Process records and add missing titles
        items = []
        for record in records:
            # Check for title in the correct column name
            title_field = 'Item Title (if not entered, website will try to make one)'
            if not record.get(title_field) and record.get('URL'):
                record[title_field] = scrape_title_from_url(record['URL'])
            
            # Convert price to float for sorting
            try:
                record['Price'] = float(record.get('Price', 0)) if record.get('Price') else 0
            except (ValueError, TypeError):
                record['Price'] = 0
            
            # Convert priority to int for sorting
            try:
                record['Priority'] = int(record.get('Priority', 0)) if record.get('Priority') else 0
            except (ValueError, TypeError):
                record['Priority'] = 0
            
            items.append(record)
        
        # Sort by priority (higher first), then by price
        items.sort(key=lambda x: (-x['Priority'], x['Price']))
        
        return render_template('registry.html', items=items)
    
    except Exception as e:
        app.logger.error(f"Error loading registry: {e}")
        flash('Unable to load registry at this time. Please try again later.', 'error')
        return render_template('registry.html', items=[])

def send_email_via_azure(to_email, subject, body, from_email=None):
    """
    Send email using Azure Communication Services
    """
    if not AZURE_EMAIL_AVAILABLE:
        return False
        
    try:
        # Get connection string from environment
        connection_string = os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')
        if not connection_string:
            app.logger.info("Azure Communication Services not configured")
            return False
            
        # Initialize the EmailClient
        email_client = EmailClient.from_connection_string(connection_string)
        
        # Set default from email
        if not from_email:
            from_email = os.environ.get('EMAIL_FROM_ADDRESS', 'noreply@your-domain.azurecomm.net')
        
        # Create the email message
        message = {
            "senderAddress": from_email,
            "recipients": {
                "to": [{"address": to_email}]
            },
            "content": {
                "subject": subject,
                "plainText": body
            }
        }
        
        # Send the email
        poller = email_client.begin_send(message)
        result = poller.result()
        
        app.logger.info(f"Email sent via Azure Communication Services. Operation ID: {result['id']}")
        return True
        
    except Exception as e:
        app.logger.error(f"Error sending email via Azure Communication Services: {e}")
        return False

def send_registry_notification_email(data):
    """
    Send registry purchase notification - tries Azure first, then SMTP fallback
    """
    to_email = os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')
    subject = f"Registry Item Purchased: {data['item_title']}"
    
    body = f"""
Someone has purchased an item from your wedding registry!

Details:
- Item: {data['item_title']}
- Purchased by: {data['name']}
- Purchase date: {data['purchase_date']}
- Item URL: {data['item_url']}

Congratulations!

---
Menke & Vacca Wedding Registry
https://menkevaccawedding.azurewebsites.net
"""
    
    # Try Azure Communication Services first
    if os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING'):
        if send_email_via_azure(to_email, subject, body):
            return True
    
    # Fall back to SMTP (existing Flask-Mail)
    try:
        if app.config.get('MAIL_USERNAME') and not app.config.get('MAIL_SUPPRESS_SEND'):
            msg = Message(
                subject=subject,
                recipients=[to_email],
                sender=app.config['MAIL_DEFAULT_SENDER'],
                body=body
            )
            mail.send(msg)
            app.logger.info("Email sent via SMTP")
            return True
        else:
            app.logger.info("SMTP email not configured - email notification skipped")
            return False
    except Exception as e:
        app.logger.error(f"Error sending email via SMTP: {e}")
        return False

@app.route('/purchase_item', methods=['POST'])
def purchase_item():
    """Handle item purchase form submission"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'purchase_date', 'item_title', 'item_url']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Update Google Sheet
        client = get_google_sheets_client()
        if not client:
            return jsonify({'error': 'Unable to connect to registry system'}), 500
        
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        records = sheet.get_all_records()
        
        # Find the row to update
        row_index = None
        for i, record in enumerate(records):
            if record.get('URL') == data['item_url']:
                row_index = i + 2  # +2 because sheets are 1-indexed and have header row
                break
        
        if row_index:
            # Update the "Bought?" and "Bought by" columns (columns 6 and 8)
            # Column order: Timestamp, URL, Priority, Image URL, Price, Bought?, Item Title, Bought by
            sheet.update_cell(row_index, 6, 'Yes')  # Column 6 is "Bought?"
            sheet.update_cell(row_index, 8, data['name'])  # Column 8 is "Bought by"
        
        # Send email notification using Azure or SMTP fallback
        try:
            email_sent = send_registry_notification_email(data)
            if email_sent:
                app.logger.info(f"Email notification sent for purchase: {data['item_title']}")
            else:
                app.logger.info(f"Email not sent - purchase recorded: {data['item_title']} by {data['name']}")
        except Exception as e:
            app.logger.error(f"Error sending email: {e}")
            # Don't fail the request if email fails
        
        return jsonify({'success': True, 'message': 'Thank you for your purchase!'})
    
    except Exception as e:
        app.logger.error(f"Error processing purchase: {e}")
        return jsonify({'error': 'An error occurred processing your purchase'}), 500

@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Start local SMTP server if in development mode
    if use_local_smtp:
        try:
            from dev_smtp_server import start_smtp_server
            smtp_thread = start_smtp_server()
            print("📧 Local SMTP server started for email testing")
        except Exception as e:
            print(f"⚠️  Could not start local SMTP server: {e}")
    
    # Set up logging
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Wedding website startup')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
