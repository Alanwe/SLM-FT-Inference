#!/usr/bin/env bash
set -euo pipefail

# VM Creation Script for Azure ML Infrastructure
# This script creates configurable Azure VMs based on settings in config.yaml

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config.yaml"
HOSTS_FILE="${SCRIPT_DIR}/hosts.txt"
POST_DEPLOY_SCRIPT="${SCRIPT_DIR}/post_deploy.sh"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/cli/azure/install-azure-cli"
        exit 1
    fi
    
    if ! command -v yq &> /dev/null; then
        log_warn "yq is not installed. Installing yq for YAML parsing..."
        # Install yq if not present
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
            sudo chmod +x /usr/local/bin/yq
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install yq || {
                log_error "Failed to install yq. Please install it manually."
                exit 1
            }
        fi
    fi
    
    # Check if logged into Azure
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

# Parse configuration from YAML
parse_config() {
    log_info "Parsing configuration from $CONFIG_FILE..."
    
    RESOURCE_GROUP=$(yq eval '.resourceGroup' "$CONFIG_FILE")
    LOCATION=$(yq eval '.location' "$CONFIG_FILE")
    VM_COUNT=$(yq eval '.vm.count' "$CONFIG_FILE")
    VM_SIZE=$(yq eval '.vm.vmSize' "$CONFIG_FILE")
    VM_NAME_PREFIX=$(yq eval '.vm.namePrefix' "$CONFIG_FILE")
    VM_PRIORITY=$(yq eval '.vm.priority' "$CONFIG_FILE")
    EVICTION_POLICY=$(yq eval '.vm.evictionPolicy' "$CONFIG_FILE")
    MAX_PRICE=$(yq eval '.vm.maxPrice' "$CONFIG_FILE")
    IMAGE_PUBLISHER=$(yq eval '.vm.image.publisher' "$CONFIG_FILE")
    IMAGE_OFFER=$(yq eval '.vm.image.offer' "$CONFIG_FILE")
    IMAGE_SKU=$(yq eval '.vm.image.sku' "$CONFIG_FILE")
    IMAGE_VERSION=$(yq eval '.vm.image.version' "$CONFIG_FILE")
    OS_DISK_SIZE=$(yq eval '.vm.osDisk.sizeGB' "$CONFIG_FILE")
    STORAGE_TYPE=$(yq eval '.vm.osDisk.storageType' "$CONFIG_FILE")
    ADMIN_USERNAME=$(yq eval '.vm.adminUsername' "$CONFIG_FILE")
    SSH_KEY_PATH=$(yq eval '.vm.sshPublicKeyPath' "$CONFIG_FILE")
    SSH_KEY_PATH="${SSH_KEY_PATH/#\~/$HOME}"
    VNET_NAME=$(yq eval '.network.vnetName' "$CONFIG_FILE")
    VNET_PREFIX=$(yq eval '.network.vnetAddressPrefix' "$CONFIG_FILE")
    SUBNET_NAME=$(yq eval '.network.subnetName' "$CONFIG_FILE")
    SUBNET_PREFIX=$(yq eval '.network.subnetAddressPrefix' "$CONFIG_FILE")
    NSG_NAME=$(yq eval '.network.nsgName' "$CONFIG_FILE")
    
    log_info "Configuration parsed successfully."
    log_info "  Resource Group: $RESOURCE_GROUP"
    log_info "  Location: $LOCATION"
    log_info "  VM Count: $VM_COUNT"
    log_info "  VM Size: $VM_SIZE"
    log_info "  Priority: $VM_PRIORITY"
}

# Create resource group
create_resource_group() {
    log_info "Creating resource group: $RESOURCE_GROUP in $LOCATION..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
    log_info "Resource group created."
}

# Create network infrastructure
create_network() {
    log_info "Creating network infrastructure..."
    
    # Create VNet
    log_info "Creating virtual network: $VNET_NAME..."
    az network vnet create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$VNET_NAME" \
        --address-prefix "$VNET_PREFIX" \
        --subnet-name "$SUBNET_NAME" \
        --subnet-prefix "$SUBNET_PREFIX" \
        --output none
    
    # Create NSG
    log_info "Creating network security group: $NSG_NAME..."
    az network nsg create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$NSG_NAME" \
        --output none
    
    # Add SSH rule
    log_info "Adding SSH rule to NSG..."
    az network nsg rule create \
        --resource-group "$RESOURCE_GROUP" \
        --nsg-name "$NSG_NAME" \
        --name "AllowSSH" \
        --priority 1000 \
        --source-address-prefixes '*' \
        --source-port-ranges '*' \
        --destination-address-prefixes '*' \
        --destination-port-ranges 22 \
        --access Allow \
        --protocol Tcp \
        --output none
    
    log_info "Network infrastructure created."
}

# Create VMs
create_vms() {
    log_info "Creating $VM_COUNT VMs..."
    
    # Clear hosts file
    > "$HOSTS_FILE"
    
    # Check if SSH key exists
    if [[ ! -f "$SSH_KEY_PATH" ]]; then
        log_error "SSH public key not found: $SSH_KEY_PATH"
        exit 1
    fi
    
    for i in $(seq 1 "$VM_COUNT"); do
        VM_NAME="${VM_NAME_PREFIX}-${i}"
        NIC_NAME="${VM_NAME}-nic"
        PUBLIC_IP_NAME="${VM_NAME}-ip"
        
        log_info "Creating VM $i/$VM_COUNT: $VM_NAME..."
        
        # Create public IP
        log_info "  Creating public IP: $PUBLIC_IP_NAME..."
        az network public-ip create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$PUBLIC_IP_NAME" \
            --sku Standard \
            --allocation-method Static \
            --output none
        
        # Create NIC
        log_info "  Creating network interface: $NIC_NAME..."
        az network nic create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$NIC_NAME" \
            --vnet-name "$VNET_NAME" \
            --subnet "$SUBNET_NAME" \
            --network-security-group "$NSG_NAME" \
            --public-ip-address "$PUBLIC_IP_NAME" \
            --output none
        
        # Build VM creation command
        VM_CREATE_CMD=(
            az vm create
            --resource-group "$RESOURCE_GROUP"
            --name "$VM_NAME"
            --location "$LOCATION"
            --nics "$NIC_NAME"
            --size "$VM_SIZE"
            --image "${IMAGE_PUBLISHER}:${IMAGE_OFFER}:${IMAGE_SKU}:${IMAGE_VERSION}"
            --os-disk-size-gb "$OS_DISK_SIZE"
            --storage-sku "$STORAGE_TYPE"
            --admin-username "$ADMIN_USERNAME"
            --ssh-key-values "@${SSH_KEY_PATH}"
            --output none
        )
        
        # Add priority settings for Spot VMs
        if [[ "$VM_PRIORITY" == "Spot" ]]; then
            VM_CREATE_CMD+=(--priority Spot)
            VM_CREATE_CMD+=(--eviction-policy "$EVICTION_POLICY")
            VM_CREATE_CMD+=(--max-price "$MAX_PRICE")
        fi
        
        # Create VM
        log_info "  Creating VM instance..."
        "${VM_CREATE_CMD[@]}"
        
        # Get public IP address
        PUBLIC_IP=$(az network public-ip show \
            --resource-group "$RESOURCE_GROUP" \
            --name "$PUBLIC_IP_NAME" \
            --query ipAddress \
            --output tsv)
        
        # Get private IP address
        PRIVATE_IP=$(az network nic show \
            --resource-group "$RESOURCE_GROUP" \
            --name "$NIC_NAME" \
            --query ipConfigurations[0].privateIPAddress \
            --output tsv)
        
        log_info "  VM created successfully!"
        log_info "    Public IP: $PUBLIC_IP"
        log_info "    Private IP: $PRIVATE_IP"
        
        # Add to hosts file
        echo "${VM_NAME} ${PUBLIC_IP} ${PRIVATE_IP}" >> "$HOSTS_FILE"
    done
    
    log_info "All VMs created successfully!"
    log_info "Hosts file saved to: $HOSTS_FILE"
}

# Run post-deployment script
run_post_deployment() {
    log_info "Running post-deployment configuration..."
    
    if [[ ! -f "$POST_DEPLOY_SCRIPT" ]]; then
        log_warn "Post-deployment script not found: $POST_DEPLOY_SCRIPT"
        log_warn "Skipping post-deployment tasks."
        return
    fi
    
    if [[ ! -x "$POST_DEPLOY_SCRIPT" ]]; then
        chmod +x "$POST_DEPLOY_SCRIPT"
    fi
    
    "$POST_DEPLOY_SCRIPT" "$CONFIG_FILE" "$HOSTS_FILE"
}

# Main execution
main() {
    log_info "Starting VM creation process..."
    
    check_prerequisites
    parse_config
    create_resource_group
    create_network
    create_vms
    run_post_deployment
    
    log_info "VM creation completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "  1. Review the hosts file: $HOSTS_FILE"
    log_info "  2. Connect to VMs using: ssh ${ADMIN_USERNAME}@<public-ip>"
    log_info "  3. Check post-deployment logs if any issues occurred"
    log_info ""
    log_info "To destroy the infrastructure, run: ./destroy_vms.sh"
}

# Handle script arguments
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [--config <config-file>]"
    echo ""
    echo "Creates Azure VMs based on configuration in config.yaml"
    echo ""
    echo "Options:"
    echo "  --config <file>    Use custom configuration file (default: config.yaml)"
    echo "  --help, -h         Show this help message"
    exit 0
fi

if [[ "${1:-}" == "--config" ]]; then
    if [[ -z "${2:-}" ]]; then
        log_error "Config file path required after --config"
        exit 1
    fi
    CONFIG_FILE="$2"
fi

main "$@"
