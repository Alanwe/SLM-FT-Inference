resource_group_name = "rg-llm-demo"
location            = "eastus2"
cluster_name        = "aks-llm-demo"

kubernetes_version = "1.29.2"

nc40_node_count = 0
nc80_node_count = 0

tags = {
  environment = "demo"
  project     = "azure-nc-llm"
}
