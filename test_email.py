#!/usr/bin/env python3
"""
Test script to verify email configuration
Run this locally to test before deploying
"""

import os
from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Try to import Azure Communication Services
try:
    from azure.communication.email import EmailClient
    AZURE_EMAIL_AVAILABLE = True
except ImportError:
    AZURE_EMAIL_AVAILABLE = False

# Load environment variables
load_dotenv()

# Create a minimal Flask app for testing
app = Flask(__name__)

# Configure email settings
app.config.update(
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME')),
    MAIL_SUPPRESS_SEND=False
)

mail = Mail(app)

def test_azure_email():
    """Test Azure Communication Services email"""
    
    if not AZURE_EMAIL_AVAILABLE:
        print("❌ Azure Communication Services not installed")
        print("💡 Install with: pip install azure-communication-email")
        return False
        
    connection_string = os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')
    if not connection_string:
        print("❌ AZURE_COMMUNICATION_CONNECTION_STRING not configured")
        return False
    
    try:
        # Initialize the EmailClient
        email_client = EmailClient.from_connection_string(connection_string)
        
        # Set sender email
        from_email = os.environ.get('EMAIL_FROM_ADDRESS', 'noreply@your-domain.azurecomm.net')
        to_email = os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')
        
        # Create the email message
        message = {
            "senderAddress": from_email,
            "recipients": {
                "to": [{"address": to_email}]
            },
            "content": {
                "subject": "Azure Communication Services Test",
                "plainText": f"""
This is a test email from Azure Communication Services!

If you receive this, your Azure email configuration is working correctly.

Test details:
- From: {from_email}
- To: {to_email}
- Service: Azure Communication Services
- Time: {os.environ.get('TZ', 'UTC')}

Congratulations! 🎉

---
Menke & Vacca Wedding Website
https://menkevaccawedding.azurewebsites.net
"""
            }
        }
        
        print("📧 Sending test email via Azure Communication Services...")
        
        # Send the email
        poller = email_client.begin_send(message)
        result = poller.result()
        
        print("✅ Azure email sent successfully!")
        print(f"📨 Sent to: {to_email}")
        print(f"📤 From: {from_email}")
        print(f"🆔 Operation ID: {result['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending Azure email: {e}")
        return False

def test_smtp_email():
    """Test SMTP email (Gmail/SendGrid fallback)"""
    
    # Check if email is configured
    if not app.config.get('MAIL_USERNAME'):
        print("❌ SMTP not configured. Please set MAIL_USERNAME and MAIL_PASSWORD in .env")
        return False
    
    try:
        with app.app_context():
            # Create test message
            msg = Message(
                subject="SMTP Email Test",
                recipients=[os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')],
                sender=app.config['MAIL_DEFAULT_SENDER'],
                body=f"""
This is a test email from SMTP!

If you receive this, SMTP email notifications are working correctly.

Test details:
- Mail server: {app.config['MAIL_SERVER']}
- Mail port: {app.config['MAIL_PORT']}
- From: {app.config['MAIL_DEFAULT_SENDER']}
- To: {os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')}

Congratulations! 🎉

---
Menke & Vacca Wedding Website
https://menkevaccawedding.azurewebsites.net
"""
            )
            
            print("📧 Sending test email via SMTP...")
            mail.send(msg)
            print("✅ SMTP email sent successfully!")
            print(f"📨 Sent to: {os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')}")
            print(f"📤 From: {app.config['MAIL_DEFAULT_SENDER']}")
            print(f"🌐 Server: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
            return True
            
    except Exception as e:
        print(f"❌ Error sending SMTP email: {e}")
        print(f"🔍 Check your email configuration in .env file")
        return False

if __name__ == '__main__':
    print("🧪 Testing email configuration...")
    print("=" * 50)
    
    # Show current configuration
    print(f"Azure Connection String: {'Set' if os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING') else 'Not set'}")
    print(f"Azure From Address: {os.environ.get('EMAIL_FROM_ADDRESS', 'Not set')}")
    print(f"Mail Server: {os.environ.get('MAIL_SERVER', 'Not set')}")
    print(f"Mail Username: {os.environ.get('MAIL_USERNAME', 'Not set')}")
    print(f"Mail Password: {'Set' if os.environ.get('MAIL_PASSWORD') else 'Not set'}")
    print(f"Email To: {os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')}")
    print("=" * 50)
    
    azure_success = False
    smtp_success = False
    
    # Test Azure Communication Services first
    if os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING'):
        print("\n📡 Testing Azure Communication Services...")
        azure_success = test_azure_email()
    else:
        print("\n⚠️  Azure Communication Services not configured")
    
    # Test SMTP fallback
    if os.environ.get('MAIL_USERNAME'):
        print("\n📧 Testing SMTP...")
        smtp_success = test_smtp_email()
    else:
        print("\n⚠️  SMTP not configured")
    
    # Results
    print("\n" + "=" * 50)
    if azure_success or smtp_success:
        print("🎉 Email test completed successfully!")
        if azure_success:
            print("✅ Azure Communication Services working")
        if smtp_success:
            print("✅ SMTP working")
        print("You can now copy these settings to Azure environment variables.")
    else:
        print("❌ No email services are working")
        print("\n💡 Setup options:")
        print("1. Azure Communication Services (recommended):")
        print("   - Create Communication Service in Azure Portal")
        print("   - Set AZURE_COMMUNICATION_CONNECTION_STRING")
        print("   - Set EMAIL_FROM_ADDRESS")
        print()
        print("2. SMTP (Gmail/SendGrid):")
        print("   - Set MAIL_USERNAME and MAIL_PASSWORD")
        print("   - For Gmail: Enable 2FA and use App Password")
        print("   - For SendGrid: Use 'apikey' as username")
