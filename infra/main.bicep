// Menke & Vacca Wedding Website - Azure Infrastructure
// Deploys: App Service, Cosmos DB, Azure OpenAI (AI Foundry), Communication Services

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Base name for all resources')
param baseName string = 'menkevaccawedding'

@description('App Service Plan SKU')
@allowed(['F1', 'B1', 'B2', 'S1'])
param appServiceSku string = 'B1'

@description('Cosmos DB free tier (limited to 1 per subscription)')
param cosmosFreeTier bool = true

@description('Azure OpenAI model deployment name')
param openAiDeploymentName string = 'gpt-4o-mini'

// ──────────────────────────────────────────────
// App Service Plan + Web App
// ──────────────────────────────────────────────

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'plan-${baseName}'
  location: location
  kind: 'linux'
  sku: {
    name: appServiceSku
  }
  properties: {
    reserved: true // Linux
  }
}

resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: baseName
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'gunicorn --bind=0.0.0.0 --timeout 600 startup:app'
      appSettings: [
        { name: 'SECRET_KEY', value: uniqueString(resourceGroup().id, baseName) }
        { name: 'FLASK_ENV', value: 'production' }
        { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
        { name: 'COSMOS_KEY', value: cosmosAccount.listKeys().primaryMasterKey }
        { name: 'COSMOS_DATABASE', value: 'wedding' }
        { name: 'COSMOS_CONTAINER', value: 'registry' }
        { name: 'AZURE_OPENAI_ENDPOINT', value: openAiAccount.properties.endpoint }
        { name: 'AZURE_OPENAI_KEY', value: openAiAccount.listKeys().key1 }
        { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAiDeploymentName }
      ]
    }
    httpsOnly: true
  }
}

// ──────────────────────────────────────────────
// Cosmos DB (NoSQL / Core SQL API)
// ──────────────────────────────────────────────

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: 'cosmos-${baseName}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: cosmosFreeTier
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: 'wedding'
  properties: {
    resource: {
      id: 'wedding'
    }
  }
}

resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'registry'
  properties: {
    resource: {
      id: 'registry'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
    }
    options: {
      throughput: 400
    }
  }
}

// ──────────────────────────────────────────────
// Azure OpenAI (AI Foundry)
// ──────────────────────────────────────────────

resource openAiAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: 'oai-${baseName}'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    customSubDomainName: 'oai-${baseName}'
  }
}

resource openAiDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAiAccount
  name: openAiDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 10 // 10K tokens per minute — plenty for registry autofill
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

// ──────────────────────────────────────────────
// Azure Communication Services (Email)
// ──────────────────────────────────────────────

resource commServices 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: 'comm-${baseName}'
  location: 'global' // Communication Services is global-only
  properties: {
    dataLocation: 'United States'
  }
}

// ──────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────

output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output openAiEndpoint string = openAiAccount.properties.endpoint
output commServicesName string = commServices.name
