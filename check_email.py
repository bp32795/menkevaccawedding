"""
Email Configuration Helper for Menke & Vacca Wedding Website

This script helps you set up email notifications for registry purchases.
"""

import os
from dotenv import load_dotenv

def check_email_config():
    """Check if email is properly configured"""
    load_dotenv()
    
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    mail_sender = os.environ.get('MAIL_DEFAULT_SENDER')
    
    print("🔧 Email Configuration Check")
    print("=" * 40)
    
    if mail_username:
        print(f"✅ MAIL_USERNAME: {mail_username}")
    else:
        print("❌ MAIL_USERNAME: Not configured")
    
    if mail_password:
        print(f"✅ MAIL_PASSWORD: {'*' * len(mail_password[:4])}{'*' * 12} (hidden)")
    else:
        print("❌ MAIL_PASSWORD: Not configured")
    
    if mail_sender:
        print(f"✅ MAIL_DEFAULT_SENDER: {mail_sender}")
    else:
        print("❌ MAIL_DEFAULT_SENDER: Not configured")
    
    print()
    
    if all([mail_username, mail_password, mail_sender]):
        print("🎉 Email is fully configured! Registry purchase notifications will be sent.")
        return True
    else:
        print("⚠️  Email is not configured. Registry purchases will work but no notifications will be sent.")
        print_setup_instructions()
        return False

def print_setup_instructions():
    """Print instructions for setting up email"""
    print()
    print("📧 How to Set Up Email Notifications:")
    print("=" * 40)
    print("1. Enable 2-Factor Authentication on your Google account")
    print("2. Go to Google Account Settings > Security > App passwords")
    print("3. Generate an app password for 'Mail'")
    print("4. Edit the .env file and add:")
    print("   MAIL_USERNAME=your-email@gmail.com")
    print("   MAIL_PASSWORD=your-16-character-app-password")
    print("   MAIL_DEFAULT_SENDER=your-email@gmail.com")
    print()
    print("5. Restart the application")
    print()
    print("📝 Example .env configuration:")
    print("   MAIL_USERNAME=bp32795@gmail.com")
    print("   MAIL_PASSWORD=abcd efgh ijkl mnop")
    print("   MAIL_DEFAULT_SENDER=bp32795@gmail.com")

def test_email_config():
    """Test email configuration by importing the Flask app"""
    try:
        from app import app, mail
        
        print()
        print("🧪 Testing Email Configuration")
        print("=" * 40)
        
        with app.app_context():
            if app.config.get('MAIL_SUPPRESS_SEND'):
                print("📧 Email sending is suppressed (normal for development without email config)")
                return False
            
            if not app.config.get('MAIL_USERNAME'):
                print("❌ No email username configured")
                return False
            
            if not app.config.get('MAIL_DEFAULT_SENDER'):
                print("❌ No default sender configured")
                return False
            
            print("✅ Email configuration looks good!")
            print(f"📤 Mail server: {app.config.get('MAIL_SERVER')}")
            print(f"📧 Username: {app.config.get('MAIL_USERNAME')}")
            print(f"📨 Default sender: {app.config.get('MAIL_DEFAULT_SENDER')}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing email config: {e}")
        return False

if __name__ == '__main__':
    print("🎊 Menke & Vacca Wedding Website - Email Setup")
    print("=" * 50)
    print()
    
    # Check environment variables
    config_ok = check_email_config()
    
    # Test Flask app configuration
    if config_ok:
        test_email_config()
    
    print()
    print("💡 Note: The website will work perfectly without email configuration.")
    print("   Registry purchases will still be recorded in Google Sheets.")
    print("   Email notifications are optional but recommended.")
