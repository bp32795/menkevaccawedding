# Quick Azure Portal Deployment Guide

Since the Azure CLI is hitting quota restrictions, let's use the Azure Portal directly. This is actually easier and more reliable for a one-time setup.

## Step 1: Open Azure Portal

1. Go to https://portal.azure.com
2. Sign in with your Microsoft account

## Step 2: Create App Service (All-in-One)

1. **Search for "App Services"** in the top search bar
2. Click **"Create"** → **"Web App"**
3. Fill in the form:

   **Project Details:**
   - Subscription: Visual Studio Enterprise Subscription (should be selected)
   - Resource Group: Click "Create new" → Name: `rg-menkevaccawedding`

   **Instance Details:**
   - Name: `menkevaccawedding` (this will be your URL)
   - Publish: `Code`
   - Runtime stack: `Python 3.11`
   - Operating System: `Linux`
   - Region: `East US` (or try `West US` if East US has issues)

   **Pricing Plans:**
   - Click "Explore pricing plans"
   - Select **"Free F1"** (1 GB RAM, 60 CPU minutes/day)
   - Click "Select"

4. Click **"Review + create"**
5. Click **"Create"**

## Step 3: Configure Environment Variables

Once the App Service is created:

1. **Go to your App Service** (`menkevaccawedding`)
2. Click **"Configuration"** in the left menu
3. Click **"Application settings"** tab
4. Add these settings (click "New application setting" for each):

```
Name: SECRET_KEY
Value: your-random-32-character-secret-key

Name: FLASK_ENV  
Value: production

Name: MAIL_SERVER
Value: smtp.sendgrid.net

Name: MAIL_PORT
Value: 587

Name: MAIL_USE_TLS
Value: true

Name: MAIL_USERNAME
Value: apikey

Name: MAIL_PASSWORD
Value: YOUR_SENDGRID_API_KEY_HERE

Name: MAIL_DEFAULT_SENDER
Value: noreply@menkevaccawedding.com

Name: GOOGLE_SHEETS_CREDS_JSON
Value: {"type":"service_account","project_id":"lively-antonym-400923",...YOUR_FULL_JSON...}

Name: SPREADSHEET_ID
Value: 1VKJ3ZPchlJ1CFpRgBygx0HnwO5nDZUnwHouZSsRLDlE
```

5. Click **"Save"** at the top

## Step 4: Configure Startup Command

1. Still in **Configuration**, click **"General settings"** tab
2. In **Startup Command**, enter: `startup.py`
3. Click **"Save"**

## Step 5: Set Up GitHub Deployment

1. Click **"Deployment Center"** in the left menu
2. Choose **"GitHub"** as the source
3. **Authorize** GitHub access if prompted
4. Select:
   - Organization: (your GitHub username)
   - Repository: `menkevaccawedding` 
   - Branch: `main`
5. Click **"Save"**

## Step 6: Set Up Email (Choose One Option)

### Option A: Azure Communication Services Email (Recommended)

Azure's native email service - more reliable and integrates better with Azure.

1. **Create Communication Services**:
   - In Azure Portal, search for "Communication Services"
   - Click "Create"
   - Resource Group: `rg-menkevaccawedding`
   - Name: `cs-menkevaccawedding`
   - Data Location: `United States`
   - Click "Review + create" → "Create"

2. **Create Email Communication Service**:
   - Search for "Email Communication Services"
   - Click "Create"
   - Resource Group: `rg-menkevaccawedding`
   - Name: `email-menkevaccawedding`
   - Click "Review + create" → "Create"

3. **Set Up Domain**:
   - Go to your Email Communication Service
   - Click "Provision domains" → "Add domain"
   - Choose "Azure managed domain" (free option)
   - Note the domain name (like `abc123.azurecomm.net`)

4. **Get Connection String**:
   - Go to Communication Services (`cs-menkevaccawedding`)
   - Click "Keys" in left menu
   - Copy the "Primary connection string"

5. **Update App Settings**:
   Replace the SendGrid settings with these in your App Service Configuration:
   ```
   Name: AZURE_COMMUNICATION_CONNECTION_STRING
   Value: [paste your connection string here]

   Name: EMAIL_FROM_ADDRESS
   Value: noreply@[your-azure-domain].azurecomm.net

   Name: EMAIL_TO_ADDRESS
   Value: bp32795@gmail.com
   ```

### Option B: SendGrid through Azure Marketplace

1. **Create SendGrid Account**:
   - In Azure Portal, search for "SendGrid"
   - Click the SendGrid marketplace offering
   - Click "Create"
   - Fill in the form and create account

2. **Get API Key** (same as before):
   - Go to SendGrid dashboard
   - Settings → API Keys → Create API Key
   - Copy the key

3. **Use SendGrid Settings** (as shown in Step 3):
   ```
   MAIL_SERVER: smtp.sendgrid.net
   MAIL_USERNAME: apikey
   MAIL_PASSWORD: [your SendGrid API key]
   ```

### Option C: Office 365/Outlook SMTP

If you have Microsoft 365:
```
MAIL_SERVER: smtp-mail.outlook.com
MAIL_PORT: 587
MAIL_USE_TLS: true
MAIL_USERNAME: your-email@outlook.com
MAIL_PASSWORD: your-app-password
```

## Step 7: App Configuration (Automatic)

Good news! Your Flask app is already configured to support all email options:

✅ **Azure Communication Services** - Uses Azure's native email service
✅ **SendGrid SMTP** - Reliable third-party email service  
✅ **Office 365/Outlook** - If you have Microsoft 365
✅ **Automatic fallback** - Tries Azure first, then SMTP

The app will automatically detect which email service is configured and use it. No code changes needed!

## Step 8: Test Your Website

## Step 8: Test Your Website

1. **URL**: https://menkevaccawedding.azurewebsites.net
2. **Check logs**: In your App Service → Monitoring → Log stream
3. **Test registry**: Try "purchasing" an item to test email

## Step 9: View Your Website

Your wedding website will be live at:
**https://menkevaccawedding.azurewebsites.net**

## Troubleshooting

**If the site doesn't start:**
1. Check App Service → Monitoring → Log stream for errors
2. Verify all environment variables are set correctly
3. Make sure startup command is `startup.py`

**If emails don't send:**
1. Verify SendGrid API key is correct
2. Check that sender email is verified in SendGrid

## Next Steps

1. **Test thoroughly** - try all pages and email functionality
2. **Custom domain** (optional) - add menkevaccawedding.com in Custom domains
3. **SSL certificate** - Azure will auto-generate for custom domains

## Cost

- **Free F1 App Service**: $0/month (has some limitations)
- **SendGrid**: Free tier (100 emails/day)
- **Total**: $0/month

Your wedding website should be fully functional! 🎉

The Free tier has some limitations (60 CPU minutes/day, goes to sleep after 20 minutes), but it's perfect for a wedding website that won't have constant traffic.
