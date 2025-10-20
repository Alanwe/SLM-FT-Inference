variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "cluster_name" {
  type        = string
  description = "AKS cluster name"
}

variable "kubernetes_version" {
  type        = string
  default     = "1.29.2"
}

variable "default_nodepool_vm_size" {
  type    = string
  default = "Standard_D8s_v5"
}

variable "system_node_count" {
  type    = number
  default = 1
}

variable "network_plugin" {
  type    = string
  default = "azure"
}

variable "enable_oidc" {
  type    = bool
  default = true
}

variable "admin_group_object_ids" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "nc40_nodepool_name" {
  type    = string
  default = "nc40h100"
}

variable "nc40_vm_size" {
  type    = string
  default = "Standard_NC40adis_H100_v5"
}

variable "nc40_node_count" {
  type    = number
  default = 0
}

variable "nc40_priority" {
  type    = string
  default = "Spot"
}

variable "nc80_nodepool_name" {
  type    = string
  default = "nc80h100"
}

variable "nc80_vm_size" {
  type    = string
  default = "Standard_NC80adis_H100_v5"
}

variable "nc80_node_count" {
  type    = number
  default = 0
}

variable "nc80_priority" {
  type    = string
  default = "Spot"
}

variable "nc40_namespace" {
  type    = string
  default = "nc40-h100"
}

variable "nc80_namespace" {
  type    = string
  default = "nc80-h100"
}
