# Email and Domain Setup Guide

## 📧 Email Configuration

### Option 1: Gmail SMTP (Easiest)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to [Google Account Settings](https://myaccount.google.com/)
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and generate password
   - Copy the 16-character password (ignore spaces)

3. **Test locally** (optional):
   - Uncomment Gmail settings in `.env` file
   - Run: `python test_email.py`

4. **Configure in Azure**:
   - Azure Portal → Your App Service → Configuration → Application settings
   - Add these settings:
   ```
   MAIL_SERVER = smtp.gmail.com
   MAIL_PORT = 587
   MAIL_USE_TLS = true
   MAIL_USERNAME = your-email@gmail.com
   MAIL_PASSWORD = your-16-character-app-password
   MAIL_DEFAULT_SENDER = your-email@gmail.com
   EMAIL_TO_ADDRESS = bp32795@gmail.com
   ```

### Option 2: SendGrid (Professional)

1. **Create SendGrid Account**: https://sendgrid.com
   - Free tier: 100 emails/day
   - Sign up and verify your email

2. **Get API Key**:
   - Dashboard → Settings → API Keys
   - Create API Key → Full Access
   - Copy the API key (starts with SG.)

3. **Verify Sender** (Important):
   - Marketing → Sender Authentication
   - Single Sender Verification → Add your email
   - Or set up domain authentication for menkevaccawedding.com

4. **Configure in Azure**:
   ```
   MAIL_SERVER = smtp.sendgrid.net
   MAIL_PORT = 587
   MAIL_USE_TLS = true
   MAIL_USERNAME = apikey
   MAIL_PASSWORD = your-sendgrid-api-key
   MAIL_DEFAULT_SENDER = noreply@menkevaccawedding.com
   EMAIL_TO_ADDRESS = bp32795@gmail.com
   ```

## 🌐 Custom Domain Setup

### Step 1: Purchase Domain
If you haven't already, purchase `menkevaccawedding.com` from:
- [GoDaddy](https://godaddy.com)
- [Namecheap](https://namecheap.com)
- [Google Domains](https://domains.google.com)
- [Cloudflare](https://cloudflare.com)

### Step 2: Configure in Azure

1. **Add Custom Domain**:
   - Azure Portal → Your App Service → Custom domains
   - Click "Add custom domain"
   - Enter: `menkevaccawedding.com`
   - Azure will show you DNS records to add

2. **Note the IP Address** shown for A record

### Step 3: DNS Configuration

In your domain registrar's DNS settings, add these records:

```
Type: A
Name: @ (or root/blank)
Value: [IP address from Azure]
TTL: 3600

Type: CNAME  
Name: www
Value: menkevaccawedding.azurewebsites.net
TTL: 3600
```

**Wait 15-30 minutes** for DNS propagation, then verify in Azure.

### Step 4: SSL Certificate

1. **Create Certificate**:
   - App Service → TLS/SSL settings
   - Private Key Certificates → "Create App Service Managed Certificate"
   - Select your domain → Create

2. **Bind Certificate**:
   - TLS/SSL bindings → "Add TLS/SSL binding"
   - Select domain and certificate
   - Choose "SNI SSL" → Add binding

### Step 5: Force HTTPS (Recommended)

- App Service → TLS/SSL settings
- Enable "HTTPS Only"

## 🧪 Testing

### Test Email:
1. Locally: `python test_email.py`
2. Production: Try purchasing a registry item

### Test Domain:
1. Visit: https://menkevaccawedding.com
2. Check SSL: Look for padlock icon
3. Test redirects: http://menkevaccawedding.com should redirect to https

## 💰 Cost Summary

- **Basic B1 App Service**: ~$13/month
- **Domain**: ~$10-15/year
- **SSL Certificate**: Free (App Service Managed)
- **Email**: 
  - Gmail: Free
  - SendGrid: Free (100 emails/day)

## 🔧 Troubleshooting

### Email Issues:
- **Gmail**: Ensure 2FA enabled and using App Password
- **SendGrid**: Verify sender email/domain authentication
- **General**: Check Azure logs for email errors

### Domain Issues:
- **DNS**: Wait 24 hours for full propagation
- **SSL**: Domain must be verified before certificate creation
- **Redirects**: Enable "HTTPS Only" in Azure

### Common Errors:
```bash
# Check DNS propagation
nslookup menkevaccawedding.com

# Test email locally
python test_email.py

# Check Azure logs
Azure Portal → App Service → Log stream
```

## 🎉 Final Steps

1. **Test everything**:
   - Visit https://menkevaccawedding.com
   - Try purchasing a registry item
   - Verify email notification arrives

2. **Update GitHub** (optional):
   - Update README.md with new domain
   - Add email configuration notes

3. **Monitor**:
   - Check Azure logs for any issues
   - Monitor email delivery rates

Your wedding website will be live at: **https://menkevaccawedding.com** 🎉
