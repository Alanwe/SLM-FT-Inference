# AKS Deployment Guide

This directory provides Bicep templates and scripts to deploy an Azure Kubernetes Service (AKS) cluster optimized for NC H100v5 GPU workloads.

## Prerequisites
- Azure CLI 2.63+
- Logged into the target subscription: `az login`
- Registered GPU resource providers:
  ```bash
  az provider register --namespace Microsoft.Compute
  az provider register --namespace Microsoft.ContainerService
  ```

## Deployment Steps

1. **Create/Update Cluster**
   
   On Linux/macOS:
   ```bash
   ./create_or_update.sh \
     --resource-group nc-h100-demo \
     --location eastus \
     --cluster-name nc-h100-aks \
     --ssh-public-key ~/.ssh/id_rsa.pub
   ```
   
   On Windows:
   ```cmd
   create_or_update.bat --resource-group nc-h100-demo --location eastus --cluster-name nc-h100-aks --ssh-public-key %USERPROFILE%\.ssh\id_rsa.pub
   ```

   The script will:
   - Create the resource group if needed.
   - Deploy `main.bicep` using the provided parameters.
   - Configure namespaces (`nc40adis` and `nc80adis`) with scheduling labels.

2. **Destroy Cluster**
   
   On Linux/macOS:
   ```bash
   ./destroy.sh --resource-group nc-h100-demo --cluster-name nc-h100-aks
   ```
   
   On Windows:
   ```cmd
   destroy.bat --resource-group nc-h100-demo --cluster-name nc-h100-aks
   ```

3. **Accessing the Cluster**
   ```bash
   az aks get-credentials -g nc-h100-demo -n nc-h100-aks --overwrite-existing
   kubectl get nodes
   ```

4. **Scheduling GPU Workloads**
   Use the node selectors and tolerations defined in the template:
   ```yaml
   nodeSelector:
     kubernetes.azure.com/agentpool: nc40adis
   tolerations:
     - key: "sku"
       value: "nc40adis"
       effect: "NoSchedule"
   ```

## Parameters
- `clusterName`: AKS cluster name.
- `location`: Azure region (ensure NC H100 availability).
- `sshRSAPublicKey`: Linux admin SSH key.
- `kubernetesVersion`: Optional AKS version override.

## Notes
- Node pools are configured as **spot (low-priority)** with **scale-to-zero** autoscaling for cost efficiency.
- System node pool uses `Standard_D8s_v5` for control-plane and services.
- Customize virtual network settings by editing `main.bicep` as needed.
