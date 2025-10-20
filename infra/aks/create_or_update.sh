#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP=""
LOCATION=""
CLUSTER_NAME=""
SSH_KEY=""
K8S_VERSION=""
PARAMS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --location)
      LOCATION="$2"
      shift 2
      ;;
    --cluster-name)
      CLUSTER_NAME="$2"
      shift 2
      ;;
    --ssh-public-key)
      SSH_KEY="$2"
      shift 2
      ;;
    --k8s-version)
      K8S_VERSION="$2"
      shift 2
      ;;
    --param)
      PARAMS+=("$2")
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$RESOURCE_GROUP" || -z "$LOCATION" || -z "$CLUSTER_NAME" || -z "$SSH_KEY" ]]; then
  echo "Usage: $0 --resource-group <rg> --location <region> --cluster-name <name> --ssh-public-key <path> [--k8s-version <ver>]" >&2
  exit 1
fi

if [[ ! -f "$SSH_KEY" ]]; then
  echo "SSH public key not found: $SSH_KEY" >&2
  exit 1
fi

az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

temp_param_file=$(mktemp)
trap 'rm -f "$temp_param_file"' EXIT

cat > "$temp_param_file" <<PARAMS
{
  "clusterName": {"value": "$CLUSTER_NAME"},
  "location": {"value": "$LOCATION"},
  "sshRSAPublicKey": {"value": "$(cat "$SSH_KEY")"}
}
PARAMS

if [[ -n "$K8S_VERSION" ]]; then
  cat > "$temp_param_file" <<PARAMS
{
  "clusterName": {"value": "$CLUSTER_NAME"},
  "location": {"value": "$LOCATION"},
  "sshRSAPublicKey": {"value": "$(cat "$SSH_KEY")"},
  "kubernetesVersion": {"value": "$K8S_VERSION"}
}
PARAMS
fi

echo "Deploying AKS cluster..."
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --name "${CLUSTER_NAME}-deployment" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters @"$temp_param_file" \
  "${PARAMS[@]}"

echo "Fetching cluster credentials..."
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --overwrite-existing

echo "Creating namespaces and labels..."
kubectl create namespace nc40adis --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace nc40adis workload=nc40adis --overwrite

kubectl create namespace nc80adis --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace nc80adis workload=nc80adis --overwrite

echo "Cluster ready: $CLUSTER_NAME"
