# Azure Communication Services Email Integration
# Add this to your Flask app to support Azure email

from azure.communication.email import EmailClient
import os

def send_email_via_azure(to_email, subject, body, from_email=None):
    """
    Send email using Azure Communication Services
    """
    try:
        # Get connection string from environment
        connection_string = os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')
        if not connection_string:
            print("Azure Communication Services not configured")
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
        
        print(f"Email sent successfully. Operation ID: {result['id']}")
        return True
        
    except Exception as e:
        print(f"Error sending email via Azure: {e}")
        return False

def send_registry_notification_azure(item_data):
    """
    Send registry purchase notification using Azure Communication Services
    """
    to_email = os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')
    subject = f"Registry Item Purchased: {item_data['item_title']}"
    
    body = f"""
Someone has purchased an item from your wedding registry!

Details:
- Item: {item_data['item_title']}
- Purchased by: {item_data['name']}
- Purchase date: {item_data['purchase_date']}
- Item URL: {item_data['item_url']}

Congratulations!

---
Menke & Vacca Wedding Registry
https://menkevaccawedding.azurewebsites.net
"""
    
    return send_email_via_azure(to_email, subject, body)

# Example integration in your purchase_item function:
def purchase_item_with_azure_email():
    """
    Updated purchase_item function that tries Azure email first, then falls back to SMTP
    """
    try:
        # ... existing Google Sheets update code ...
        
        # Try Azure Communication Services first
        if os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING'):
            success = send_registry_notification_azure(data)
            if success:
                return jsonify({'message': 'Item purchased and notification sent successfully!'})
        
        # Fall back to existing Flask-Mail SMTP
        # ... existing email code ...
        
    except Exception as e:
        return jsonify({'error': f'Error processing purchase: {str(e)}'}), 500
