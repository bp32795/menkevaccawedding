# Azure Deployment Setup for Menke & Vacca Wedding Website

This guide will help you deploy your wedding website to Azure with proper email configuration.

## Prerequisites

1. Azure CLI installed
2. An Azure subscription
3. Domain name (menkevaccawedding.com) ready for DNS configuration

## Option 1: Azure Communication Services Email (Recommended)

### Step 1: Create Azure Resources

```bash
# Login to Azure
az login

# Create resource group
az group create --name rg-menkevaccawedding --location "East US"

# Create App Service Plan
az appservice plan create --name plan-menkevaccawedding --resource-group rg-menkevaccawedding --sku B1 --is-linux

# Create Web App
az webapp create --resource-group rg-menkevaccawedding --plan plan-menkevaccawedding --name menkevaccawedding --runtime "PYTHON|3.11"

# Create Communication Services resource
az communication create --name cs-menkevaccawedding --resource-group rg-menkevaccawedding --data-location "United States"
```

### Step 2: Configure Email Domain

```bash
# Create Email Communication Service
az communication email create --name email-menkevaccawedding --resource-group rg-menkevaccawedding

# Add your domain (you'll need to verify DNS records)
az communication email domain create --domain-name menkevaccawedding.com --email-service-name email-menkevaccawedding --resource-group rg-menkevaccawedding
```

### Step 3: Get Connection Strings

```bash
# Get Communication Services connection string
az communication list-key --name cs-menkevaccawedding --resource-group rg-menkevaccawedding

# Get Email service endpoint
az communication email show --name email-menkevaccawedding --resource-group rg-menkevaccawedding
```

### Step 4: Configure App Settings

```bash
# Set environment variables in Azure App Service
az webapp config appsettings set --resource-group rg-menkevaccawedding --name menkevaccawedding --settings \
    FLASK_ENV=production \
    SECRET_KEY="your-production-secret-key-here" \
    GOOGLE_SHEETS_CREDS_JSON="your-google-service-account-json" \
    SPREADSHEET_ID="your-google-sheet-id" \
    AZURE_COMMUNICATION_CONNECTION_STRING="your-connection-string" \
    EMAIL_FROM_ADDRESS="noreply@menkevaccawedding.com" \
    EMAIL_TO_ADDRESS="bp32795@gmail.com"
```

## Option 2: SendGrid (Alternative)

If you prefer SendGrid (which has a good free tier):

### Step 1: Create SendGrid Account

```bash
# Create SendGrid account through Azure Marketplace
az provider register --namespace Microsoft.SaaS
```

### Step 2: Configure SendGrid

```bash
# Set SendGrid configuration
az webapp config appsettings set --resource-group rg-menkevaccawedding --name menkevaccawedding --settings \
    MAIL_SERVER="smtp.sendgrid.net" \
    MAIL_PORT="587" \
    MAIL_USE_TLS="true" \
    MAIL_USERNAME="apikey" \
    MAIL_PASSWORD="your-sendgrid-api-key" \
    MAIL_DEFAULT_SENDER="noreply@menkevaccawedding.com"
```

## Option 3: Gmail SMTP (Simple but less scalable)

For a simple wedding website, you can use Gmail SMTP:

```bash
az webapp config appsettings set --resource-group rg-menkevaccawedding --name menkevaccawedding --settings \
    MAIL_SERVER="smtp.gmail.com" \
    MAIL_PORT="587" \
    MAIL_USE_TLS="true" \
    MAIL_USERNAME="your-gmail@gmail.com" \
    MAIL_PASSWORD="your-app-password" \
    MAIL_DEFAULT_SENDER="your-gmail@gmail.com"
```

## DNS Configuration

Add these DNS records to your domain:

```
# For custom domain
CNAME   www     menkevaccawedding.azurewebsites.net
A       @       [App Service IP]

# For email verification (if using Azure Communication Services)
TXT     @       [Verification token from Azure]
```

## Deployment Commands

```bash
# Deploy using GitHub Actions (recommended)
# Push to main branch and GitHub Actions will handle deployment

# Or deploy directly using Azure CLI
az webapp deployment source config --resource-group rg-menkevaccawedding --name menkevaccawedding --repo-url https://github.com/yourusername/menkevaccawedding --branch main --manual-integration
```

## Cost Estimation

- App Service B1: ~$13/month
- Azure Communication Services: Pay per email sent (~$0.0025 per email)
- SendGrid Free Tier: 100 emails/day free
- Gmail: Free (but with daily limits)

## Security Recommendations

1. Use Azure Key Vault for secrets in production
2. Enable HTTPS only
3. Configure custom domain with SSL certificate
4. Set up application insights for monitoring

## Next Steps

1. Run the Azure CLI commands above
2. Update your GitHub secrets with the publish profile
3. Push to main branch to trigger deployment
4. Configure DNS records
5. Test email functionality
