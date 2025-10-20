resource "azurerm_kubernetes_cluster" "this" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "${var.cluster_name}-dns"
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name       = "system"
    vm_size    = var.default_nodepool_vm_size
    node_count = var.system_node_count
    mode       = "System"
  }

  identity {
    type = "SystemAssigned"
  }

  oidc_issuer_enabled       = var.enable_oidc
  workload_identity_enabled = var.enable_oidc

  network_profile {
    network_plugin = var.network_plugin
  }

  azure_active_directory_role_based_access_control {
    managed                = true
    admin_group_object_ids = var.admin_group_object_ids
  }

  tags = var.tags
}

resource "azurerm_kubernetes_cluster_node_pool" "nc40" {
  name                  = var.nc40_nodepool_name
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id
  vm_size               = var.nc40_vm_size
  node_count            = var.nc40_node_count
  priority              = var.nc40_priority
  mode                  = "User"
  eviction_policy       = var.nc40_priority == "Spot" ? "Delete" : null
  max_pods              = 110
  enable_auto_scaling   = true
  min_count             = 0
  max_count             = max(1, var.nc40_node_count)
}

resource "azurerm_kubernetes_cluster_node_pool" "nc80" {
  name                  = var.nc80_nodepool_name
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id
  vm_size               = var.nc80_vm_size
  node_count            = var.nc80_node_count
  priority              = var.nc80_priority
  mode                  = "User"
  eviction_policy       = var.nc80_priority == "Spot" ? "Delete" : null
  max_pods              = 110
  enable_auto_scaling   = true
  min_count             = 0
  max_count             = max(1, var.nc80_node_count)
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.this.name
}

output "kube_config" {
  value = azurerm_kubernetes_cluster.this.kube_config_raw
}
