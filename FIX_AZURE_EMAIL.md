# Fix Azure Communication Services Domain Error

## Error: "DomainNotLinked"
This means your Azure Communication Services doesn't have a properly configured email domain.

## 🚀 Quick Fix: Use Azure Managed Domain (5 minutes)

### Step 1: Add Azure Managed Domain
1. **Azure Portal** → Search "Email Communication Services"
2. **Click your service** (e.g., `menkevaccawedding-email`)
3. **Provision domains** → **Add domain**
4. **Select "Azure managed domain"** → **Add**
5. **Copy the domain** (looks like: `donotreply@1234567890.azurecomm.net`)

### Step 2: Connect to Communication Service
1. **Go to your Communication Service** (e.g., `menkevaccawedding-comms`)
2. **Email** → **Connect domain**
3. **Select your Email Communication Service**
4. **Choose the Azure managed domain you just created**
5. **Connect**

### Step 3: Update App Service
1. **Go to your App Service** → **Configuration** → **Application settings**
2. **Update EMAIL_FROM_ADDRESS**:
   ```
   EMAIL_FROM_ADDRESS = donotreply@1234567890.azurecomm.net
   ```
   (Use the actual domain from Step 1)
3. **Save**

### Step 4: Test
Try purchasing a registry item to test email notifications.

---

## 🎯 Professional Fix: Custom Domain

If you want emails from `noreply@menkevaccawedding.com`:

### Step 1: Add Custom Domain
1. **Email Communication Services** → **Provision domains** → **Add domain**
2. **Select "Custom domain"**
3. **Domain name**: `menkevaccawedding.com`
4. **Add**

### Step 2: DNS Configuration
Azure will show you DNS records to add. In your domain registrar (GoDaddy, etc.):

```
Type: TXT
Name: @ (or root)
Value: [verification string from Azure]

Type: TXT
Name: selector1._domainkey
Value: [DKIM key 1 from Azure]

Type: TXT
Name: selector2._domainkey  
Value: [DKIM key 2 from Azure]
```

### Step 3: Wait for Verification
- Usually takes 15-30 minutes
- Check status in Azure Portal

### Step 4: Connect Domain
1. **Communication Service** → **Email** → **Connect domain**
2. **Select your Email Communication Service**
3. **Choose your verified custom domain**
4. **Connect**

### Step 5: Update App Service
```
EMAIL_FROM_ADDRESS = noreply@menkevaccawedding.com
```

---

## 🔧 Alternative: Use SMTP Instead

If Azure Communication Services is too complex, use Gmail SMTP:

### Step 1: Configure Gmail
1. **Enable 2-Factor Authentication** on Gmail
2. **Generate App Password**: Google Account → Security → App passwords
3. **Copy the 16-character password**

### Step 2: Update Azure App Service
```
MAIL_SERVER = smtp.gmail.com
MAIL_PORT = 587
MAIL_USE_TLS = true
MAIL_USERNAME = your-email@gmail.com
MAIL_PASSWORD = your-16-character-app-password
MAIL_DEFAULT_SENDER = your-email@gmail.com
EMAIL_TO_ADDRESS = bp32795@gmail.com
```

### Step 3: Remove Azure Email Settings
Delete or leave empty:
```
AZURE_COMMUNICATION_CONNECTION_STRING = (leave empty)
EMAIL_FROM_ADDRESS = (leave empty)
```

---

## 🧪 Test Email Configuration

Run this locally to test:

```bash
python test_email.py
```

Or test in production by purchasing a registry item.

---

## 💡 Troubleshooting

### Common Issues:

1. **"Domain verification failed"**
   - Wait 24 hours for DNS propagation
   - Double-check DNS records are exact

2. **"InvalidSender"**
   - Make sure EMAIL_FROM_ADDRESS matches your configured domain
   - For Azure managed: use the exact domain provided
   - For custom: use your verified domain

3. **"Unauthorized"**
   - Check AZURE_COMMUNICATION_CONNECTION_STRING is correct
   - Verify Communication Service has Email connected

4. **SMTP errors**
   - For Gmail: ensure App Password (not regular password)
   - For SendGrid: use 'apikey' as username

### Check Current Configuration:
- Azure Portal → Communication Service → Email → Domains
- Should show "Verified" status for your domain

## 🎯 Recommended Approach

**For testing**: Use Azure managed domain (fastest)
**For production**: Use custom domain (professional)
**For simplicity**: Use Gmail SMTP (most reliable)

The Azure managed domain is perfect for getting email working immediately!
