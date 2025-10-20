# Terraform Infrastructure

This module provisions an AKS cluster configured for Azure NC H100 GPU workloads.

## Features

- Resource group creation
- AKS cluster with system node pool
- User node pools for `Standard_NC40adis_H100_v5` and `Standard_NC80adis_H100_v5`
- Spot/low-priority nodes scaled to zero by default
- Namespaces labeled for autoscaler integration

## Usage

```bash
cd infra/terraform
terraform init
terraform apply -var-file=examples/aks.hcl \
  -var="resource_group_name=rg-llm-demo" \
  -var="location=eastus2" \
  -var="cluster_name=aks-llm-demo"
```

After apply, extract kubeconfig:

```bash
terraform output -raw kube_config > kubeconfig
export KUBECONFIG=$(pwd)/kubeconfig
```

Scale GPU node pools when needed:

```bash
az aks nodepool scale \
  --resource-group rg-llm-demo \
  --cluster-name aks-llm-demo \
  --name nc40h100 \
  --node-count 2
```

