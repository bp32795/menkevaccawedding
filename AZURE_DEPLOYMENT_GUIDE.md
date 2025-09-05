# Complete Azure Deployment Guide

## Overview

This guide will help you deploy your wedding website to Azure with email functionality using SendGrid SMTP. The deployment includes:

- Azure App Service for hosting
- SendGrid for email notifications
- Continuous deployment from GitHub
- HTTPS and custom domain support

## Prerequisites

1. **Azure CLI** installed on your machine
2. **Azure subscription** (free tier is sufficient)
3. **SendGrid account** (can be created through Azure Marketplace)
4. **GitHub repository** with your code
5. **Google Sheets service account** JSON credentials

## Step 1: Deploy Azure Resources

Run the PowerShell deployment script:

```powershell
# Navigate to your project directory
cd c:\Users\bp327\code\menkevaccawedding

# Run the deployment script
.\deploy-azure.ps1
```

This creates:
- Resource Group: `rg-menkevaccawedding`
- App Service Plan: `plan-menkevaccawedding` (B1 tier)
- Web App: `menkevaccawedding`

## Step 2: Set Up SendGrid

### Option A: Through Azure Portal
1. Go to Azure Portal
2. Search for "SendGrid" in the marketplace
3. Create a SendGrid account
4. Get your API key from SendGrid dashboard

### Option B: Direct SendGrid Registration
1. Go to https://sendgrid.com
2. Sign up for a free account (100 emails/day)
3. Generate an API key
4. Verify your sender identity

## Step 3: Configure Environment Variables

Run the configuration script with your credentials:

```powershell
.\configure-azure.ps1 `
    -GoogleSheetsJson '{"type":"service_account",...your-full-json...}' `
    -SpreadsheetId "1VKJ3ZPchlJ1CFpRgBygx0HnwO5nDZUnwHouZSsRLDlE" `
    -SendGridApiKey "SG.your-sendgrid-api-key-here"
```

## Step 4: Set Up GitHub Actions Deployment

1. Get the publish profile:
```bash
az webapp deployment list-publishing-profiles --resource-group rg-menkevaccawedding --name menkevaccawedding --xml
```

2. In your GitHub repository:
   - Go to Settings > Secrets and variables > Actions
   - Add a new secret: `AZUREAPPSERVICE_PUBLISHPROFILE`
   - Paste the XML content from step 1

3. Push to main branch to trigger deployment

## Step 5: Configure Custom Domain (Optional)

If you want to use `menkevaccawedding.com`:

```bash
# Add custom domain
az webapp config hostname add --webapp-name menkevaccawedding --resource-group rg-menkevaccawedding --hostname menkevaccawedding.com

# Configure SSL certificate (Azure will auto-generate)
az webapp config ssl bind --certificate-thumbprint auto --ssl-type SNI --name menkevaccawedding --resource-group rg-menkevaccawedding
```

### DNS Configuration
Add these DNS records to your domain:
```
Type: CNAME
Name: www
Value: menkevaccawedding.azurewebsites.net

Type: A
Name: @
Value: [Get IP from Azure Portal]
```

## Email Configuration Options

### Current Setup: SendGrid (Recommended)
- **Cost**: Free tier (100 emails/day)
- **Reliability**: High
- **Setup**: Simple SMTP configuration

### Alternative: Gmail SMTP
- **Cost**: Free
- **Reliability**: Good for low volume
- **Limitations**: Daily sending limits

### Alternative: Azure Communication Services
- **Cost**: Pay per email (~$0.0025 per email)
- **Reliability**: Very high
- **Setup**: Requires custom implementation (not SMTP)

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `FLASK_ENV` | Environment | `production` |
| `MAIL_SERVER` | SMTP server | `smtp.sendgrid.net` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USE_TLS` | Use TLS | `true` |
| `MAIL_USERNAME` | SMTP username | `apikey` |
| `MAIL_PASSWORD` | SendGrid API key | `SG.abc123...` |
| `MAIL_DEFAULT_SENDER` | From email | `noreply@menkevaccawedding.com` |
| `GOOGLE_SHEETS_CREDS_JSON` | Service account JSON | `{"type":"service_account"...}` |
| `SPREADSHEET_ID` | Google Sheet ID | `1VKJ3ZP...` |

## Testing the Deployment

1. Visit your app: `https://menkevaccawedding.azurewebsites.net`
2. Test the registry page
3. Try purchasing an item to test email notifications
4. Check Azure App Service logs for any errors

## Monitoring and Maintenance

### View Logs
```bash
az webapp log tail --resource-group rg-menkevaccawedding --name menkevaccawedding
```

### Monitor Performance
- Use Azure Application Insights (can be enabled in portal)
- Monitor SendGrid email delivery rates
- Check Google Sheets API usage

## Cost Estimation

- **App Service B1**: ~$13/month
- **SendGrid Free**: $0 (up to 100 emails/day)
- **Azure Storage**: ~$1/month (for logs)
- **Total**: ~$14/month

## Troubleshooting

### Common Issues

1. **Email not sending**
   - Check SendGrid API key is correct
   - Verify sender email is verified in SendGrid
   - Check Azure App Service logs

2. **Google Sheets not updating**
   - Verify service account has edit permissions
   - Check SPREADSHEET_ID is correct
   - Ensure service account JSON is properly escaped

3. **App not starting**
   - Check startup.py is configured
   - Verify Python version (3.11)
   - Check requirements.txt dependencies

### Debug Commands
```bash
# Check app settings
az webapp config appsettings list --resource-group rg-menkevaccawedding --name menkevaccawedding

# View real-time logs
az webapp log tail --resource-group rg-menkevaccawedding --name menkevaccawedding

# Restart app
az webapp restart --resource-group rg-menkevaccawedding --name menkevaccawedding
```

## Security Best Practices

1. **Never commit secrets** to GitHub
2. **Use Azure Key Vault** for production secrets (optional upgrade)
3. **Enable HTTPS only** (done by scripts)
4. **Regular security updates** for dependencies
5. **Monitor access logs** in Azure

## Next Steps After Deployment

1. Test all functionality thoroughly
2. Set up monitoring and alerts
3. Configure backup strategy
4. Plan for traffic scaling if needed
5. Set up custom domain and SSL
6. Configure email templates and styling

Your wedding website should now be fully deployed and functional on Azure! 🎉
