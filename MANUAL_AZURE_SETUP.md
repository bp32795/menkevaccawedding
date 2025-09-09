# Manual Azure Setup Guide
# Use this if Azure CLI is having PATH issues

## Step 1: Azure Portal Setup

1. **Go to Azure Portal**: https://portal.azure.com
2. **Create a Resource Group**:
   - Search for "Resource groups"
   - Click "Create"
   - Name: `rg-menkevaccawedding`
   - Region: `East US`
   - Click "Review + create"

3. **Create App Service Plan**:
   - Search for "App Service plans"
   - Click "Create"
   - Resource Group: `rg-menkevaccawedding`
   - Name: `plan-menkevaccawedding`
   - Operating System: `Linux`
   - Pricing Tier: `Basic B1` (about $13/month)
   - Click "Review + create"

4. **Create Web App**:
   - Search for "App Services"
   - Click "Create" > "Web App"
   - Resource Group: `rg-menkevaccawedding`
   - Name: `menkevaccawedding` (this will be your URL)
   - Runtime stack: `Python 3.11`
   - App Service Plan: `plan-menkevaccawedding`
   - Click "Review + create"

## Step 2: Configure Web App

1. **Go to your Web App** (`menkevaccawedding`)
2. **Configuration** (in left menu):
   - Click "Configuration"
   - Click "General settings" tab
   - Set Startup Command: `startup.py`
   - Click "Save"

3. **Environment Variables**:
   - Still in Configuration, click "Application settings" tab
   - Add these settings (click "New application setting" for each):

   ```
   Name: SECRET_KEY
   Value: [generate a random 32-character string]

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
   Value: [your SendGrid API key - get from sendgrid.com]

   Name: MAIL_DEFAULT_SENDER
   Value: noreply@menkevaccawedding.com

   Name: GOOGLE_SHEETS_CREDS_JSON
   Value: [your Google service account JSON - IMPORTANT: escape all \n as \\n]

   Name: SPREADSHEET_ID
   Value: 1VKJ3ZPchlJ1CFpRgBygx0HnwO5nDZUnwHouZSsRLDlE
   ```

   - Click "Save" after adding all settings

## Important: Google Sheets JSON Format

**Critical**: The `GOOGLE_SHEETS_CREDS_JSON` must include ALL parts of the private key:

1. **Include the header/footer lines**: 
   - `-----BEGIN PRIVATE KEY-----`
   - `-----END PRIVATE KEY-----`

2. **Include ALL newlines**: The private key has embedded newlines that are required

3. **Escape newlines for Azure**: Replace `\n` with `\\n` in the JSON

**Example of correct format**:
```json
{
  "type": "service_account",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhk...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "your-service@project.iam.gserviceaccount.com",
  ...
}
```

**Use the value from your `.env.new` file** - it's already properly formatted!

## Step 3: Set Up SendGrid

1. **Create SendGrid Account**:
   - Go to https://sendgrid.com
   - Sign up for free account
   - Verify your email

2. **Get API Key**:
   - In SendGrid dashboard, go to Settings > API Keys
   - Click "Create API Key"
   - Choose "Full Access" for simplicity
   - Copy the API key (use this for MAIL_PASSWORD above)

3. **Verify Sender**:
   - Go to Marketing > Sender Authentication
   - Verify a single sender email (like your Gmail)
   - Or set up domain authentication for menkevaccawedding.com

## Step 4: Deploy Code

1. **Deployment Center** (in your Web App):
   - Click "Deployment Center" in left menu
   - Choose "GitHub" as source
   - Authorize and select your repository
   - Branch: `main`
   - Click "Save"

2. **Alternative: Get Publish Profile**:
   - In your Web App overview, click "Download publish profile"
   - In GitHub: Settings > Secrets > Actions
   - Add secret: `AZUREAPPSERVICE_PUBLISHPROFILE`
   - Paste the contents of the downloaded file
   - Push to main branch to trigger deployment

## Step 5: Test Your Website

1. **URL**: https://menkevaccawedding.azurewebsites.net
2. **Test Registry**: Try purchasing an item to test email
3. **Check Logs**: In Web App > Log stream to see any errors

## Step 6: Custom Domain (Optional)

1. **In Azure**:
   - Web App > Custom domains
   - Add custom domain: `menkevaccawedding.com`
   - Follow DNS verification steps

2. **DNS Settings** (in your domain registrar):
   ```
   Type: CNAME
   Name: www
   Value: menkevaccawedding.azurewebsites.net

   Type: A
   Name: @
   Value: [IP shown in Azure custom domains]
   ```

## Step 7: SSL Certificate

1. **In Azure**:
   - Web App > TLS/SSL settings
   - Click "Add certificate"
   - Choose "App Service Managed Certificate"
   - Select your domain

## Troubleshooting

- **App not starting**: Check Configuration > General settings for startup command
- **Environment variables**: Make sure all are set correctly in Configuration
- **Email not working**: Verify SendGrid API key and sender verification
- **Google Sheets**: Ensure service account JSON is valid and has edit permissions

## Cost Summary

- **Basic B1 App Service**: ~$13/month
- **SendGrid Free**: 100 emails/day free
- **Total**: ~$13/month

Your wedding website will be live at: https://menkevaccawedding.azurewebsites.net
