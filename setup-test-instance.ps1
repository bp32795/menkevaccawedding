param(
    [string]$ResourceGroup = "rg-menkevaccawedding",
    [string]$ProductionAppName = "menkevaccawedding",
    [string]$TestAppName = "menkevaccawedding-test",
    [string]$DnsZone = "menkexvacca.com",
    [string]$TestHostname = "test.menkexvacca.com"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI is required. Install it from https://aka.ms/installazurecliwindows."
}

az account show --output none
if ($LASTEXITCODE -ne 0) {
    throw "Sign in to Azure with 'az login' before running this script."
}

$productionApp = az webapp show `
    --resource-group $ResourceGroup `
    --name $ProductionAppName | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "Production app '$ProductionAppName' was not found."
}

$planName = Split-Path $productionApp.appServicePlanId -Leaf
$testAppExists = az webapp show `
    --resource-group $ResourceGroup `
    --name $TestAppName `
    --query name `
    --output tsv `
    2>$null

if (-not $testAppExists) {
    Write-Host "Creating test web app '$TestAppName' on plan '$planName'..."
    az webapp create `
        --resource-group $ResourceGroup `
        --plan $planName `
        --name $TestAppName `
        --runtime "PYTHON:3.11" `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create test web app '$TestAppName'."
    }
}

Write-Host "Copying production app settings to the test app..."
$settingsFile = Join-Path ([System.IO.Path]::GetTempPath()) "$TestAppName-settings.json"
try {
    $productionSettings = az webapp config appsettings list `
        --resource-group $ResourceGroup `
        --name $ProductionAppName | ConvertFrom-Json
    $settingsByName = [ordered]@{}
    foreach ($setting in $productionSettings) {
        $settingsByName[$setting.name] = $setting.value
    }
    $settingsByName | ConvertTo-Json -Depth 5 | Set-Content -Path $settingsFile -Encoding utf8

    az webapp config appsettings set `
        --resource-group $ResourceGroup `
        --name $TestAppName `
        --settings "@$settingsFile" `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to copy production app settings."
    }
}
finally {
    Remove-Item $settingsFile -ErrorAction SilentlyContinue
}

$productionConfig = az webapp config show `
    --resource-group $ResourceGroup `
    --name $ProductionAppName | ConvertFrom-Json

$runtimeConfigArguments = @(
    "webapp", "config", "set",
    "--resource-group", $ResourceGroup,
    "--name", $TestAppName,
    "--ftps-state", $productionConfig.ftpsState,
    "--min-tls-version", $productionConfig.minTlsVersion,
    "--http20-enabled", $productionConfig.http20Enabled,
    "--output", "none"
)
if ($productionConfig.appCommandLine) {
    $runtimeConfigArguments += @("--startup-file", $productionConfig.appCommandLine)
}

& az @runtimeConfigArguments
if ($LASTEXITCODE -ne 0) {
    throw "Unable to copy production runtime configuration."
}

az webapp update `
    --resource-group $ResourceGroup `
    --name $TestAppName `
    --https-only true `
    --output none

$defaultHostname = az webapp show `
    --resource-group $ResourceGroup `
    --name $TestAppName `
    --query defaultHostName `
    --output tsv

Write-Host "Creating DNS record for '$TestHostname'..."
$recordName = $TestHostname.Substring(0, $TestHostname.Length - $DnsZone.Length).TrimEnd('.')
az network dns record-set cname set-record `
    --resource-group $ResourceGroup `
    --zone-name $DnsZone `
    --record-set-name $recordName `
    --cname $defaultHostname `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create the DNS CNAME record."
}

Write-Host "Binding '$TestHostname' to the test app..."
az webapp config hostname add `
    --resource-group $ResourceGroup `
    --webapp-name $TestAppName `
    --hostname $TestHostname `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Unable to bind the custom hostname. Wait for DNS propagation and rerun the script."
}

Write-Host "Creating and binding an Azure managed TLS certificate..."
az webapp config ssl create `
    --resource-group $ResourceGroup `
    --name $TestAppName `
    --hostname $TestHostname `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create the managed certificate. Wait for DNS propagation and rerun the script."
}

$certificateThumbprint = az webapp config ssl show `
    --resource-group $ResourceGroup `
    --certificate-name $TestHostname `
    --query thumbprint `
    --output tsv

az webapp config ssl bind `
    --resource-group $ResourceGroup `
    --name $TestAppName `
    --certificate-thumbprint $certificateThumbprint `
    --ssl-type SNI `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Unable to bind the managed certificate to '$TestHostname'."
}

Write-Host "Test instance configured: https://$TestHostname"
Write-Host "Deploy application code through the GitHub Actions test stage."