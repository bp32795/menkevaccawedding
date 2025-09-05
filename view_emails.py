"""
Email Viewer for Development
View emails sent to the local SMTP server during development
"""

import os
import json
from datetime import datetime
import glob

def view_emails():
    """View all emails sent to the local SMTP server"""
    email_dir = "email_logs"
    
    if not os.path.exists(email_dir):
        print(f"📧 No email logs found. Directory '{email_dir}' doesn't exist.")
        print("   Start the Flask app to begin logging emails.")
        return
    
    email_files = glob.glob(os.path.join(email_dir, "email_*.json"))
    
    if not email_files:
        print(f"📧 No emails found in '{email_dir}' directory.")
        print("   Try purchasing a registry item to send a test email.")
        return
    
    # Sort by filename (which includes timestamp)
    email_files.sort(reverse=True)
    
    print(f"📧 Found {len(email_files)} emails in '{email_dir}':")
    print("=" * 80)
    
    for i, email_file in enumerate(email_files, 1):
        try:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            timestamp = datetime.fromisoformat(email_data['timestamp'])
            
            print(f"\n📨 Email #{i} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   File: {os.path.basename(email_file)}")
            print(f"   From: {email_data['from']}")
            print(f"   To: {', '.join(email_data['to'])}")
            print(f"   Subject: {email_data['subject']}")
            print(f"   Body Preview: {email_data['body'][:100]}...")
            
            if i <= 3:  # Show full body for first 3 emails
                print(f"\n   Full Body:")
                print("   " + "-" * 50)
                for line in email_data['body'].split('\n'):
                    print(f"   {line}")
                print("   " + "-" * 50)
            
        except Exception as e:
            print(f"❌ Error reading {email_file}: {e}")
    
    print(f"\n💡 Tip: Delete files in '{email_dir}' to clear email history")

def clear_emails():
    """Clear all email logs"""
    email_dir = "email_logs"
    
    if not os.path.exists(email_dir):
        print(f"📧 No email logs to clear. Directory '{email_dir}' doesn't exist.")
        return
    
    email_files = glob.glob(os.path.join(email_dir, "email_*.json"))
    
    if not email_files:
        print(f"📧 No emails to clear in '{email_dir}' directory.")
        return
    
    confirm = input(f"🗑️  Delete {len(email_files)} email logs? (y/N): ")
    if confirm.lower() in ['y', 'yes']:
        for email_file in email_files:
            os.remove(email_file)
        print(f"✅ Cleared {len(email_files)} email logs")
    else:
        print("❌ Email clear cancelled")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        clear_emails()
    else:
        view_emails()
        
        print("\n" + "=" * 80)
        print("📧 Email Viewer Commands:")
        print("   python view_emails.py       - View all emails")
        print("   python view_emails.py clear - Clear all email logs")
