# Azure Service Principal (Cost Management Reader)

# Login & set subscription
az login
az account set --subscription <SUBSCRIPTION_ID>

# Create SP with minimal role
az ad sp create-for-rbac --name cost-dashboard-sp   --role "Cost Management Reader"   --scopes /subscriptions/<SUBSCRIPTION_ID>   --sdk-auth

# Output includes clientId, clientSecret, tenantId; put into .env
