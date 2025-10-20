terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.113"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

module "aks" {
  source              = "./modules/aks"
  cluster_name        = var.cluster_name
  kubernetes_version  = var.kubernetes_version
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
  default_nodepool_vm_size = var.default_nodepool_vm_size
  system_node_count        = var.system_node_count
  network_plugin           = var.network_plugin
  enable_oidc              = var.enable_oidc
  admin_group_object_ids   = var.admin_group_object_ids

  nc40_nodepool_name = var.nc40_nodepool_name
  nc40_vm_size       = var.nc40_vm_size
  nc40_node_count    = var.nc40_node_count
  nc40_priority      = var.nc40_priority

  nc80_nodepool_name = var.nc80_nodepool_name
  nc80_vm_size       = var.nc80_vm_size
  nc80_node_count    = var.nc80_node_count
  nc80_priority      = var.nc80_priority
}

resource "kubernetes_namespace" "nc40" {
  metadata {
    name = var.nc40_namespace
    annotations = {
      "azure.microsoft.com/cluster-autoscaler-enabled" = "true"
    }
  }
  depends_on = [module.aks]
}

resource "kubernetes_namespace" "nc80" {
  metadata {
    name = var.nc80_namespace
    annotations = {
      "azure.microsoft.com/cluster-autoscaler-enabled" = "true"
    }
  }
  depends_on = [module.aks]
}
