"""
Local SMTP Server for Development
A simple SMTP server that runs alongside the Flask app for testing email functionality
"""

import socketserver
import threading
import email
from datetime import datetime
import json
import os
import re

class SimpleSMTPHandler(socketserver.BaseRequestHandler):
    """Simple SMTP handler for development"""
    
    def handle(self):
        """Handle SMTP connection"""
        try:
            self.data_dir = "email_logs"
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            
            # Send initial greeting
            self.request.send(b"220 localhost Simple Mail Server\r\n")
            
            mail_from = ""
            mail_to = []
            mail_data = ""
            in_data_mode = False
            
            while True:
                data = self.request.recv(1024).decode('utf-8').strip()
                if not data:
                    break
                
                print(f"📨 SMTP Command: {data}")
                
                if data.upper().startswith('HELO') or data.upper().startswith('EHLO'):
                    self.request.send(b"250 Hello\r\n")
                
                elif data.upper().startswith('MAIL FROM:'):
                    mail_from = self._extract_email(data)
                    self.request.send(b"250 OK\r\n")
                
                elif data.upper().startswith('RCPT TO:'):
                    mail_to.append(self._extract_email(data))
                    self.request.send(b"250 OK\r\n")
                
                elif data.upper() == 'DATA':
                    self.request.send(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                    in_data_mode = True
                    mail_data = ""
                
                elif in_data_mode:
                    if data == '.':
                        # End of data
                        self._save_email(mail_from, mail_to, mail_data)
                        self.request.send(b"250 OK Message accepted\r\n")
                        in_data_mode = False
                    else:
                        mail_data += data + "\n"
                
                elif data.upper() == 'QUIT':
                    self.request.send(b"221 Bye\r\n")
                    break
                
                else:
                    self.request.send(b"250 OK\r\n")
                    
        except Exception as e:
            print(f"❌ SMTP Handler error: {e}")
    
    def _extract_email(self, line):
        """Extract email address from SMTP command"""
        match = re.search(r'<([^>]+)>', line)
        if match:
            return match.group(1)
        return line.split(':')[1].strip()
    
    def _save_email(self, mail_from, mail_to, mail_data):
        """Save email to file and log to console"""
        try:
            # Parse the email
            msg = email.message_from_string(mail_data)
            
            # Extract email details
            email_data = {
                'timestamp': datetime.now().isoformat(),
                'from': mail_from,
                'to': mail_to,
                'subject': msg.get('Subject', 'No Subject'),
                'headers': dict(msg.items()),
                'body': self._get_body(msg)
            }
            
            # Save to file
            filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False)
            
            # Log to console
            print(f"\n📨 Email Received ({datetime.now().strftime('%H:%M:%S')})")
            print(f"   From: {mail_from}")
            print(f"   To: {', '.join(mail_to)}")
            print(f"   Subject: {email_data['subject']}")
            print(f"   Saved: {filepath}")
            print(f"   Body Preview: {email_data['body'][:100]}...")
            
        except Exception as e:
            print(f"❌ Error saving email: {e}")
    
    def _get_body(self, msg):
        """Extract email body text"""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode('utf-8')
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8')
        except Exception as e:
            print(f"Warning: Could not decode email body: {e}")
        return "Could not decode email body"

class ThreadedSMTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded SMTP server"""
    allow_reuse_address = True

def start_smtp_server(host='localhost', port=1025):
    """Start the SMTP server in a separate thread"""
    def run_server():
        try:
            server = ThreadedSMTPServer((host, port), SimpleSMTPHandler)
            print(f"📧 Dev SMTP Server started on {host}:{port}")
            print(f"📁 Email logs will be saved to: email_logs/")
            print(f"🚀 Starting email server...")
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n📧 SMTP Server stopped")
            server.shutdown()
        except Exception as e:
            print(f"❌ SMTP Server error: {e}")
    
    # Run server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread

if __name__ == '__main__':
    print("🎯 Starting Development SMTP Server...")
    print("   Host: localhost")
    print("   Port: 1025")
    print("   Email logs: email_logs/")
    print("   Press Ctrl+C to stop")
    
    try:
        server = ThreadedSMTPServer(('localhost', 1025), SimpleSMTPHandler)
        print(f"📧 Dev SMTP Server started on localhost:1025")
        print(f"📁 Email logs will be saved to: email_logs/")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 SMTP Server stopped")
        server.shutdown()
    except Exception as e:
        print(f"❌ Error: {e}")
