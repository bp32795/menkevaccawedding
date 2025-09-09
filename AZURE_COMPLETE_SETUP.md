# Complete Azure Setup Guide
## Domain + Email + Hosting All in Azure

## 🌐 Step 1: Purchase Domain in Azure

### Method 1: Azure App Service Domains (Easiest)

1. **Purchase Domain**:
   - Azure Portal → Search "App Service domains"
   - Click "Add" → Search for `menkevaccawedding.com`
   - Select domain → Complete purchase (~$12-15/year)
   - Choose your subscription and resource group

2. **Auto-Configuration**:
   - Azure automatically creates DNS zone
   - Domain is ready to use immediately
   - No external DNS configuration needed

3. **Link to App Service**:
   - Go to your App Service (`menkevaccawedding`)
   - Custom domains → "Add custom domain"
   - Select your Azure domain from dropdown
   - Click "Validate" → "Add custom domain"

### Method 2: External Domain with Azure DNS

If you prefer to buy elsewhere (GoDaddy, etc.):

1. **Create DNS Zone**:
   - Azure Portal → "DNS zones" → Create
   - Zone name: `menkevaccawedding.com`
   - Resource group: Same as your app

2. **Update Nameservers**:
   - Copy the 4 nameservers from Azure DNS zone
   - Update at your domain registrar
   - Wait 24-48 hours for propagation

## 📧 Step 2: Azure Communication Services Email

### Setup Azure Communication Services

1. **Create Communication Service**:
   - Azure Portal → "Communication Services" → Create
   - Name: `menkevaccawedding-comms`
   - Resource group: Same as your app
   - Data location: Choose your region

2. **Get Connection String**:
   - Go to your Communication Service
   - Keys → Copy "Primary connection string"

3. **Create Email Communication Service**:
   - Azure Portal → "Email Communication Services" → Create
   - Name: `menkevaccawedding-email`
   - Resource group: Same as your app

4. **Configure Domain**:
   - Go to your Email Communication Service
   - Provision domains → Add domain
   - Choose "Azure managed domain" (easiest) or "Custom domain"

### Option A: Azure Managed Domain (Easiest)

1. **Use Azure Subdomain**:
   - Select "Azure managed domain"
   - You'll get: `donotreply@[random].azurecomm.net`
   - Ready to use immediately
   - No DNS configuration needed

### Option B: Custom Domain (Professional)

1. **Add Custom Domain**:
   - Select "Custom domain"
   - Enter: `menkevaccawedding.com`
   - Follow DNS verification steps

2. **DNS Records Required**:
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

3. **Wait for Verification**: Usually 15-30 minutes

### Connect Email to Communication Service

1. **Connect Domains**:
   - Communication Service → Email → Connect domain
   - Select your Email Communication Service
   - Choose the domain you configured

## 🔧 Step 3: Configure App Service

Add these environment variables in Azure App Service:

```
# Azure Communication Services
AZURE_COMMUNICATION_CONNECTION_STRING = [from Communication Service → Keys]
EMAIL_FROM_ADDRESS = noreply@menkevaccawedding.com (or Azure managed domain)
EMAIL_TO_ADDRESS = bp32795@gmail.com

# Keep existing Google Sheets config
GOOGLE_SHEETS_CREDS_JSON = [your existing JSON]
SPREADSHEET_ID = 1VKJ3ZPchlJ1CFpRgBygx0HnwO5nDZUnwHouZSsRLDlE
SECRET_KEY = [generate random 32-character string]
FLASK_ENV = production
```

## 🔒 Step 4: SSL Certificate

1. **Create Certificate**:
   - App Service → TLS/SSL settings
   - Private Key Certificates → "Create App Service Managed Certificate"
   - Select your domain → Create

2. **Bind Certificate**:
   - TLS/SSL bindings → "Add TLS/SSL binding"
   - Select domain and certificate → "SNI SSL"

3. **Force HTTPS**:
   - TLS/SSL settings → Enable "HTTPS Only"

## 💰 Step 5: Cost Summary (All Azure)

- **App Service Basic B1**: ~$13/month
- **Domain Registration**: ~$12-15/year
- **Communication Services**: 
  - First 1,000 emails/month: Free
  - Additional emails: $0.0025 each
- **DNS Zone**: $0.50/month (if using external domain)
- **SSL Certificate**: Free (App Service Managed)

**Total**: ~$13-14/month + domain annual fee

## 🧪 Step 6: Testing

### Test Email Setup:

1. **Add to your `.env` for local testing**:
   ```
   AZURE_COMMUNICATION_CONNECTION_STRING=your-connection-string
   EMAIL_FROM_ADDRESS=noreply@yourdomain.azurecomm.net
   EMAIL_TO_ADDRESS=bp32795@gmail.com
   ```

2. **Run test**: `python test_email.py`

3. **Test in production**: Try purchasing a registry item

### Test Domain:
- Visit: `https://menkevaccawedding.com`
- Verify SSL certificate
- Test redirect from HTTP to HTTPS

## 🔧 Advanced Configuration

### Custom Email Templates:
You can enhance the email formatting by updating the email body in `send_registry_notification_email()`:

```python
body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ background-color: #f8f9fa; padding: 20px; }}
        .content {{ padding: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>Registry Purchase Notification</h2>
    </div>
    <div class="content">
        <p>Someone has purchased an item from your wedding registry!</p>
        
        <h3>Details:</h3>
        <ul>
            <li><strong>Item:</strong> {data['item_title']}</li>
            <li><strong>Purchased by:</strong> {data['name']}</li>
            <li><strong>Purchase date:</strong> {data['purchase_date']}</li>
            <li><strong>Item URL:</strong> <a href="{data['item_url']}">View Item</a></li>
        </ul>
        
        <p>Congratulations! 🎉</p>
        
        <hr>
        <p><small>
            Menke & Vacca Wedding Registry<br>
            <a href="https://menkevaccawedding.com">https://menkevaccawedding.com</a>
        </small></p>
    </div>
</body>
</html>
"""
```

### Monitoring:
- Azure Monitor → Application Insights for detailed logging
- Communication Services → Metrics for email delivery stats
- App Service → Log stream for real-time logs

## 🎉 Benefits of All-Azure Setup

✅ **Single Bill**: Everything on one Azure invoice  
✅ **Integrated**: All services work seamlessly together  
✅ **Scalable**: Easy to upgrade if you get popular  
✅ **Secure**: Built-in security and compliance  
✅ **Support**: Single support channel for everything  
✅ **Monitoring**: Unified dashboard for all services  

Your wedding website will be fully hosted, secured, and managed entirely within Azure! 🚀
