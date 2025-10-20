#!/usr/bin/env bash
set -euo pipefail

# VM Destruction Script
# This script destroys all resources created by create_vms.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config.yaml"

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
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
}

# Parse configuration
parse_config() {
    log_info "Parsing configuration..."
    RESOURCE_GROUP=$(yq eval '.resourceGroup' "$CONFIG_FILE")
    log_info "Resource Group: $RESOURCE_GROUP"
}

# Destroy infrastructure
destroy_infrastructure() {
    log_warn "This will delete the entire resource group: $RESOURCE_GROUP"
    log_warn "All VMs, networks, and associated resources will be permanently deleted."
    echo -n "Are you sure you want to continue? (yes/no): "
    read -r confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        log_info "Destruction cancelled."
        exit 0
    fi
    
    log_info "Deleting resource group: $RESOURCE_GROUP..."
    if az group delete --name "$RESOURCE_GROUP" --yes --no-wait; then
        log_info "Resource group deletion initiated."
        log_info "This may take several minutes to complete."
        log_info "You can check the status in the Azure Portal."
    else
        log_error "Failed to delete resource group."
        exit 1
    fi
}

# Main execution
main() {
    log_info "Starting VM infrastructure destruction..."
    
    check_prerequisites
    parse_config
    destroy_infrastructure
    
    log_info "Destruction process initiated successfully!"
}

# Handle script arguments
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [--config <config-file>] [--force]"
    echo ""
    echo "Destroys all Azure resources created by create_vms.sh"
    echo ""
    echo "Options:"
    echo "  --config <file>    Use custom configuration file (default: config.yaml)"
    echo "  --force            Skip confirmation prompt"
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
