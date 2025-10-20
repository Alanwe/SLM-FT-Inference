variable "cluster_name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "kubernetes_version" { type = string }
variable "default_nodepool_vm_size" { type = string }
variable "system_node_count" { type = number }
variable "network_plugin" { type = string }
variable "enable_oidc" { type = bool }
variable "admin_group_object_ids" { type = list(string) }
variable "tags" { type = map(string) }

variable "nc40_nodepool_name" { type = string }
variable "nc40_vm_size" { type = string }
variable "nc40_node_count" { type = number }
variable "nc40_priority" { type = string }

variable "nc80_nodepool_name" { type = string }
variable "nc80_vm_size" { type = string }
variable "nc80_node_count" { type = number }
variable "nc80_priority" { type = string }
