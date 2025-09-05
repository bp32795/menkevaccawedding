# Azure Deployment Script for Menke & Vacca Wedding Website
# PowerShell version for Windows users

# Configuration
$RESOURCE_GROUP = "rg-menkevaccawedding"
$LOCATION = "East US" 
$APP_NAME = "menkevaccawedding"
$PLAN_NAME = "plan-menkevaccawedding"

Write-Host "Starting Azure deployment for Menke & Vacca Wedding Website" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check if Azure CLI is installed
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "Azure CLI is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
    exit 1
}

# Login to Azure
Write-Host "Logging into Azure..." -ForegroundColor Blue
az login

# Create resource group
Write-Host "Creating resource group: $RESOURCE_GROUP" -ForegroundColor Blue
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service Plan (Free tier to avoid quota issues)
Write-Host "Creating App Service Plan: $PLAN_NAME" -ForegroundColor Blue
az appservice plan create `
    --name $PLAN_NAME `
    --resource-group $RESOURCE_GROUP `
    --sku F1 `
    --is-linux

# Create Web App
Write-Host "Creating Web App: $APP_NAME" -ForegroundColor Blue
az webapp create `
    --resource-group $RESOURCE_GROUP `
    --plan $PLAN_NAME `
    --name $APP_NAME `
    --runtime "PYTHON:3.11"

# Configure Web App settings
Write-Host "Configuring Web App settings..." -ForegroundColor Blue
az webapp config set `
    --resource-group $RESOURCE_GROUP `
    --name $APP_NAME `
    --startup-file "startup.py"

# Get the URL
$APP_URL = az webapp show --resource-group $RESOURCE_GROUP --name $APP_NAME --query defaultHostName --output tsv

Write-Host ""
Write-Host "Azure resources created successfully!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Web App: https://$APP_URL" -ForegroundColor Cyan
Write-Host "Resource Group: $RESOURCE_GROUP" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure environment variables using the configure-azure.ps1 script" -ForegroundColor White
Write-Host "2. Set up continuous deployment from GitHub" -ForegroundColor White
Write-Host "3. Configure custom domain (optional)" -ForegroundColor White
Write-Host ""
Write-Host "For email, we recommend using SendGrid" -ForegroundColor Yellow
Write-Host "Run configure-azure.ps1 with your credentials to complete setup" -ForegroundColor Gray
