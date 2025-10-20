#!/usr/bin/env bash
set -euo pipefail

# VM Status Check Script
# This script checks the status of created VMs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config.yaml"
HOSTS_FILE="${SCRIPT_DIR}/hosts.txt"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed."
        exit 1
    fi
    
    if ! command -v yq &> /dev/null; then
        log_error "yq is not installed."
        exit 1
    fi
    
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi
}

# Parse configuration
parse_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    RESOURCE_GROUP=$(yq eval '.resourceGroup' "$CONFIG_FILE")
    ADMIN_USERNAME=$(yq eval '.vm.adminUsername' "$CONFIG_FILE")
}

# Check resource group status
check_resource_group() {
    log_info "Checking resource group: $RESOURCE_GROUP"
    
    if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        log_info "✓ Resource group exists"
        
        LOCATION=$(az group show --name "$RESOURCE_GROUP" --query location -o tsv)
        log_info "  Location: $LOCATION"
    else
        log_warn "✗ Resource group does not exist"
        return 1
    fi
}

# Check VMs status
check_vms() {
    log_info "Checking VMs in resource group..."
    
    VMS=$(az vm list --resource-group "$RESOURCE_GROUP" --query "[].{Name:name, Status:powerState, Size:hardwareProfile.vmSize}" -o tsv)
    
    if [[ -z "$VMS" ]]; then
        log_warn "No VMs found in resource group"
        return 1
    fi
    
    echo ""
    echo "VM Status:"
    echo "=========================================="
    az vm list --resource-group "$RESOURCE_GROUP" --show-details \
        --query "[].{Name:name, PowerState:powerState, Size:hardwareProfile.vmSize, PublicIP:publicIps, PrivateIP:privateIps}" \
        -o table
    echo ""
}

# Test SSH connectivity
test_ssh_connectivity() {
    if [[ ! -f "$HOSTS_FILE" ]]; then
        log_warn "Hosts file not found: $HOSTS_FILE"
        log_warn "Skipping SSH connectivity test"
        return
    fi
    
    log_info "Testing SSH connectivity to VMs..."
    echo ""
    
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            VM_NAME=$(echo "$line" | awk '{print $1}')
            PUBLIC_IP=$(echo "$line" | awk '{print $2}')
            
            echo -n "Testing $VM_NAME ($PUBLIC_IP)... "
            
            if timeout 10 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
                "${ADMIN_USERNAME}@${PUBLIC_IP}" "echo 'OK'" &>/dev/null; then
                echo -e "${GREEN}✓ Connected${NC}"
            else
                echo -e "${RED}✗ Failed${NC}"
            fi
        fi
    done < "$HOSTS_FILE"
    echo ""
}

# Check GPU availability
check_gpu_status() {
    if [[ ! -f "$HOSTS_FILE" ]]; then
        log_warn "Hosts file not found: $HOSTS_FILE"
        return
    fi
    
    log_info "Checking GPU status on VMs..."
    echo ""
    
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            VM_NAME=$(echo "$line" | awk '{print $1}')
            PUBLIC_IP=$(echo "$line" | awk '{print $2}')
            
            echo "GPU Status for $VM_NAME ($PUBLIC_IP):"
            echo "----------------------------------------"
            
            if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                "${ADMIN_USERNAME}@${PUBLIC_IP}" "nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits" 2>/dev/null; then
                echo ""
            else
                echo -e "${YELLOW}nvidia-smi not available or GPU not detected${NC}"
                echo ""
            fi
        fi
    done < "$HOSTS_FILE"
}

# Check Docker status
check_docker_status() {
    if [[ ! -f "$HOSTS_FILE" ]]; then
        log_warn "Hosts file not found: $HOSTS_FILE"
        return
    fi
    
    log_info "Checking Docker status on VMs..."
    echo ""
    
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            VM_NAME=$(echo "$line" | awk '{print $1}')
            PUBLIC_IP=$(echo "$line" | awk '{print $2}')
            
            echo -n "Docker on $VM_NAME ($PUBLIC_IP): "
            
            DOCKER_VERSION=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                "${ADMIN_USERNAME}@${PUBLIC_IP}" "docker --version 2>/dev/null" || echo "Not installed")
            
            if [[ "$DOCKER_VERSION" == "Not installed" ]]; then
                echo -e "${RED}✗ Not installed${NC}"
            else
                echo -e "${GREEN}✓ $DOCKER_VERSION${NC}"
            fi
        fi
    done < "$HOSTS_FILE"
    echo ""
}

# Show cost estimate
show_cost_estimate() {
    log_info "Estimated daily costs:"
    
    VM_COUNT=$(az vm list --resource-group "$RESOURCE_GROUP" --query "length([])" -o tsv)
    
    if [[ "$VM_COUNT" -eq 0 ]]; then
        log_warn "No VMs found to calculate costs"
        return
    fi
    
    VM_SIZES=$(az vm list --resource-group "$RESOURCE_GROUP" --query "[].hardwareProfile.vmSize" -o tsv | sort | uniq -c)
    
    echo ""
    echo "VM Size Distribution:"
    echo "$VM_SIZES"
    echo ""
    echo "Note: Check Azure pricing calculator for accurate costs:"
    echo "https://azure.microsoft.com/pricing/calculator/"
    echo ""
}

# Main execution
main() {
    log_info "VM Infrastructure Status Check"
    log_info "================================"
    echo ""
    
    check_prerequisites
    parse_config
    
    if ! check_resource_group; then
        log_warn "Infrastructure not deployed or resource group deleted"
        exit 1
    fi
    
    check_vms
    test_ssh_connectivity
    check_docker_status
    check_gpu_status
    show_cost_estimate
    
    log_info "Status check completed!"
}

# Handle script arguments
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [--config <config-file>]"
    echo ""
    echo "Checks the status of VMs created by create_vms.sh"
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
