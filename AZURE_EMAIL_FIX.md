# Azure Communication Services Email Fix

## Problem
You're getting this error:
```
(DomainNotLinked) The specified sender domain has not been linked.
```

## Quick Fix Options

### Option 1: Use Azure Managed Domain (Easiest)

1. **Go to Azure Portal** → Your Email Communication Service
2. **Provision domains** → **Add domain**
3. **Select "Azure managed domain"**
4. **Copy the domain** (looks like: `donotreply@[random].azurecomm.net`)
5. **Update environment variable**:
   ```
   EMAIL_FROM_ADDRESS = donotreply@[your-random-id].azurecomm.net
   ```

### Option 2: Link Custom Domain

1. **Go to Azure Portal** → Your Email Communication Service
2. **Provision domains** → **Add domain**
3. **Select "Custom domain"**
4. **Enter**: `menkevaccawedding.com`
5. **Add DNS records** to your domain:
   ```
   Type: TXT
   Name: @
   Value: [Azure verification string]
   
   Type: TXT
   Name: selector1._domainkey
   Value: [Azure DKIM key 1]
   
   Type: TXT
   Name: selector2._domainkey
   Value: [Azure DKIM key 2]
   ```
6. **Wait for verification** (15-30 minutes)
7. **Connect domain** to Communication Service

### Option 3: Use SMTP Fallback (Gmail/SendGrid)

If you want to skip Azure email for now, configure SMTP instead:

**Gmail Option:**
```
MAIL_SERVER = smtp.gmail.com
MAIL_PORT = 587
MAIL_USE_TLS = true
MAIL_USERNAME = your-email@gmail.com
MAIL_PASSWORD = your-16-char-app-password
MAIL_DEFAULT_SENDER = your-email@gmail.com
EMAIL_TO_ADDRESS = bp32795@gmail.com
```

**SendGrid Option:**
```
MAIL_SERVER = smtp.sendgrid.net
MAIL_PORT = 587
MAIL_USE_TLS = true
MAIL_USERNAME = apikey
MAIL_PASSWORD = your-sendgrid-api-key
MAIL_DEFAULT_SENDER = noreply@menkevaccawedding.com
EMAIL_TO_ADDRESS = bp32795@gmail.com
```

## Testing

1. **Update your environment variables** in Azure App Service
2. **Restart** your app
3. **Try purchasing** a registry item
4. **Check logs** for success/failure

## Current Status Check

Based on your logs, the system is:
- ✅ Connecting to Azure Communication Services
- ✅ Initializing EmailClient successfully  
- ❌ Failing because domain isn't linked
- 🔄 Should fallback to SMTP if configured

## Recommended Quick Fix

**Use Azure Managed Domain** (Option 1) - it's the fastest way to get email working:

1. Go to Azure Portal
2. Find your Email Communication Service
3. Add an Azure managed domain
4. Update `EMAIL_FROM_ADDRESS` with the provided domain
5. Test again

The system will automatically fallback to SMTP if Azure fails, so you can also just configure Gmail/SendGrid as a backup.
