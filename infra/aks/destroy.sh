#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP=""
CLUSTER_NAME=""
DELETE_RG=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --cluster-name)
      CLUSTER_NAME="$2"
      shift 2
      ;;
    --delete-resource-group)
      DELETE_RG=true
      shift 1
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$RESOURCE_GROUP" || -z "$CLUSTER_NAME" ]]; then
  echo "Usage: $0 --resource-group <rg> --cluster-name <name> [--delete-resource-group]" >&2
  exit 1
fi

echo "Deleting AKS cluster $CLUSTER_NAME..."
az aks delete --name "$CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --yes --no-wait || true

echo "Waiting for cluster deletion to finish..."
az resource wait --deleted --ids \
  "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerService/managedClusters/$CLUSTER_NAME"

if [[ "$DELETE_RG" == true ]]; then
  echo "Deleting resource group $RESOURCE_GROUP..."
  az group delete --name "$RESOURCE_GROUP" --yes --no-wait
fi
