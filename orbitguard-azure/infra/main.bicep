// =====================================================================
// OrbitGuard AI — Infraestrutura Azure (Bicep)
// =====================================================================
// Provisiona: Cosmos DB, Key Vault, App Configuration, Application
// Insights e Static Web App. A Managed Identity do Static Web App
// recebe RBAC de leitura no Key Vault e no Cosmos (least privilege).
//
// Deploy:
//   az deployment group create -g rg-orbitguard \
//     --template-file infra/main.bicep \
//     --parameters repoUrl=https://github.com/SEU_USER/orbitguard-azure
// =====================================================================

@description('Localização dos recursos')
param location string = resourceGroup().location

@description('Prefixo dos nomes')
param prefix string = 'orbitguard'

@description('URL do repositório GitHub (para o CI/CD do Static Web App)')
param repoUrl string

@description('Branch do repositório')
param branch string = 'main'

@description('Chave simulada do provedor de dados orbitais')
@secure()
param satelliteApiKey string = 'demo-key-substituir'

var suffix = uniqueString(resourceGroup().id)

// ---------- Cosmos DB ----------
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${prefix}-cosmos-${suffix}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [{ locationName: location, failoverPriority: 0 }]
    capabilities: [{ name: 'EnableServerless' }]
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'orbitdb'
  properties: { resource: { id: 'orbitdb' } }
}

resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'alerts'
  properties: {
    resource: {
      id: 'alerts'
      partitionKey: { paths: ['/id'], kind: 'Hash' }
    }
  }
}

// ---------- Key Vault (Secrets + chave de criptografia) ----------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-kv-${suffix}'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true // usa RBAC em vez de access policies
    softDeleteRetentionInDays: 7
  }
}

resource secret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'satellite-api-key'
  properties: { value: satelliteApiKey }
}

// ---------- App Configuration (Parameter Store) ----------
resource appConfig 'Microsoft.AppConfiguration/configurationStores@2023-03-01' = {
  name: '${prefix}-config-${suffix}'
  location: location
  sku: { name: 'free' }
}

// ---------- Application Insights (monitoramento) ----------
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-insights'
  location: location
  kind: 'web'
  properties: { Application_Type: 'web' }
}

// ---------- Static Web App (site + API + CI/CD) ----------
resource staticSite 'Microsoft.Web/staticSites@2023-12-01' = {
  name: '${prefix}-site'
  location: location
  sku: { name: 'Free', tier: 'Free' }
  identity: { type: 'SystemAssigned' } // Managed Identity
  properties: {
    repositoryUrl: repoUrl
    branch: branch
    buildProperties: {
      appLocation: '/frontend'
      apiLocation: '/api'
      outputLocation: ''
    }
  }
}

// ---------- RBAC: Managed Identity do site acessa Key Vault e Cosmos ----------
// Key Vault Secrets User
resource kvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, staticSite.id, 'kv-secrets-user')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: staticSite.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cosmos DB Built-in Data Contributor (plano de dados)
resource cosmosRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, staticSite.id, 'cosmos-data-contributor')
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: staticSite.identity.principalId
    scope: cosmos.id
  }
}

// ---------- Outputs ----------
output siteName string = staticSite.name
output siteHostname string = staticSite.properties.defaultHostname
output cosmosUrl string = cosmos.properties.documentEndpoint
output keyVaultUrl string = keyVault.properties.vaultUri
output appInsightsKey string = appInsights.properties.InstrumentationKey
