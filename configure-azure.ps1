# Azure Configuration Script - Run this after deploy-azure.ps1
# This script configures SendGrid and sets up environment variables

param(
    [Parameter(Mandatory=$true)]
    [string]$GoogleSheetsJson,
    
    [Parameter(Mandatory=$true)]
    [string]$SpreadsheetId,
    
    [Parameter(Mandatory=$true)]
    [string]$SendGridApiKey,
    
    [string]$ResourceGroup = "rg-menkevaccawedding",
    [string]$AppName = "menkevaccawedding",
    [string]$SecretKey = $null
)

Write-Host "🔧 Configuring Azure App Service for Wedding Website" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green

# Generate a random secret key if not provided
if (-not $SecretKey) {
    $SecretKey = [System.Web.Security.Membership]::GeneratePassword(32, 8)
    Write-Host "🔑 Generated random secret key" -ForegroundColor Yellow
}

# Configure environment variables
Write-Host "⚙️  Setting environment variables..." -ForegroundColor Blue

$settings = @(
    "SECRET_KEY=$SecretKey",
    "FLASK_ENV=production",
    "MAIL_SERVER=smtp.sendgrid.net",
    "MAIL_PORT=587",
    "MAIL_USE_TLS=true",
    "MAIL_USERNAME=apikey",
    "MAIL_PASSWORD=$SendGridApiKey",
    "MAIL_DEFAULT_SENDER=noreply@menkevaccawedding.com",
    "GOOGLE_SHEETS_CREDS_JSON=$GoogleSheetsJson",
    "SPREADSHEET_ID=$SpreadsheetId"
)

# Apply settings to Azure App Service
foreach ($setting in $settings) {
    Write-Host "   Setting: $($setting.Split('=')[0])" -ForegroundColor Gray
}

az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $AppName `
    --settings $settings

# Enable HTTPS only
Write-Host "🔒 Enabling HTTPS only..." -ForegroundColor Blue
az webapp update --resource-group $ResourceGroup --name $AppName --https-only true

# Configure startup command
Write-Host "🚀 Configuring startup command..." -ForegroundColor Blue
az webapp config set --resource-group $ResourceGroup --name $AppName --startup-file "startup.py"

# Get app information
$appInfo = az webapp show --resource-group $ResourceGroup --name $AppName | ConvertFrom-Json
$appUrl = "https://$($appInfo.defaultHostName)"

Write-Host ""
Write-Host "✅ Configuration completed successfully!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host "🌐 Your wedding website: $appUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Configuration Summary:" -ForegroundColor Yellow
Write-Host "   Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "   App Name: $AppName" -ForegroundColor White
Write-Host "   Email Provider: SendGrid" -ForegroundColor White
Write-Host "   HTTPS Only: Enabled" -ForegroundColor White
Write-Host "   Google Sheets: Configured" -ForegroundColor White
Write-Host ""

# Bind SSL certificate for custom domain if managed cert exists
Write-Host "🔐 Checking for managed SSL certificate..." -ForegroundColor Blue
$certs = az webapp config ssl list --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
$managedCert = $certs | Where-Object { $_.subjectName -eq "menkevaccawedding.com" } | Select-Object -First 1
if ($managedCert) {
    Write-Host "   Found managed certificate, binding SSL..." -ForegroundColor Green
    az webapp config ssl bind `
        --certificate-thumbprint $managedCert.thumbprint `
        --ssl-type SNI `
        --resource-group $ResourceGroup `
        --name $AppName
    Write-Host "   ✅ SSL certificate bound to custom domain" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  No managed certificate found for menkevaccawedding.com" -ForegroundColor Yellow
    Write-Host "   Run the Bicep deployment with customDomainName parameter first, then re-run this script." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Push your code to GitHub to trigger deployment" -ForegroundColor White
Write-Host "2. Configure custom domain (optional):" -ForegroundColor White
Write-Host "   az webapp config hostname add --webapp-name $AppName --resource-group $ResourceGroup --hostname menkevaccawedding.com" -ForegroundColor Gray
Write-Host "3. Set up SSL certificate for custom domain" -ForegroundColor White
Write-Host "4. Test your website at: $appUrl" -ForegroundColor White
Write-Host ""

# Example usage information
Write-Host "💡 Example usage:" -ForegroundColor Cyan
Write-Host '.\configure-azure.ps1 -GoogleSheetsJson "{\""type\"":\""service_account\"",..." -SpreadsheetId "1VKJ3ZP..." -SendGridApiKey "SG.abc123..."' -ForegroundColor Gray
