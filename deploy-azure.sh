#!/bin/bash

# Azure Deployment Script for Menke & Vacca Wedding Website
# This script creates all necessary Azure resources for your wedding website

# Configuration
RESOURCE_GROUP="rg-menkevaccawedding"
LOCATION="East US"
APP_NAME="menkevaccawedding"
PLAN_NAME="plan-menkevaccawedding"

echo "🎯 Starting Azure deployment for Menke & Vacca Wedding Website"
echo "=================================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Login to Azure
echo "🔐 Logging into Azure..."
az login

# Create resource group
echo "📁 Creating resource group: $RESOURCE_GROUP"
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Create App Service Plan (B1 - Basic tier, suitable for wedding website)
echo "📋 Creating App Service Plan: $PLAN_NAME"
az appservice plan create \
    --name $PLAN_NAME \
    --resource-group $RESOURCE_GROUP \
    --sku B1 \
    --is-linux

# Create Web App
echo "🌐 Creating Web App: $APP_NAME"
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --name $APP_NAME \
    --runtime "PYTHON|3.11"

# Configure Web App settings
echo "⚙️  Configuring Web App settings..."
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --startup-file "startup.py"

# Get the URL
APP_URL=$(az webapp show --resource-group $RESOURCE_GROUP --name $APP_NAME --query defaultHostName --output tsv)

echo ""
echo "✅ Azure resources created successfully!"
echo "=================================================="
echo "📱 Web App: https://$APP_URL"
echo "📁 Resource Group: $RESOURCE_GROUP"
echo ""
echo "🔧 Next Steps:"
echo "1. Configure environment variables in Azure App Service:"
echo "   az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $APP_NAME --settings \\"
echo "       SECRET_KEY=\"your-secret-key\" \\"
echo "       FLASK_ENV=\"production\" \\"
echo "       MAIL_SERVER=\"smtp.sendgrid.net\" \\"
echo "       MAIL_PORT=\"587\" \\"
echo "       MAIL_USE_TLS=\"true\" \\"
echo "       MAIL_USERNAME=\"apikey\" \\"
echo "       MAIL_PASSWORD=\"your-sendgrid-api-key\" \\"
echo "       MAIL_DEFAULT_SENDER=\"noreply@menkevaccawedding.com\" \\"
echo "       GOOGLE_SHEETS_CREDS_JSON=\"your-service-account-json\" \\"
echo "       SPREADSHEET_ID=\"your-google-sheet-id\""
echo ""
echo "2. Set up continuous deployment from GitHub:"
echo "   - Go to Azure Portal > App Service > Deployment Center"
echo "   - Connect to your GitHub repository"
echo "   - Or use the publish profile in GitHub Actions"
echo ""
echo "3. Get the publish profile for GitHub Actions:"
echo "   az webapp deployment list-publishing-profiles --resource-group $RESOURCE_GROUP --name $APP_NAME --xml"
echo ""
echo "4. Configure custom domain (optional):"
echo "   az webapp config hostname add --webapp-name $APP_NAME --resource-group $RESOURCE_GROUP --hostname menkevaccawedding.com"
echo ""
echo "📧 For email, we recommend using SendGrid:"
echo "   - Create a SendGrid account through Azure Marketplace"
echo "   - Or use the Azure Communication Services (requires custom implementation)"
echo ""
