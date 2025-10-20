#!/usr/bin/env bash
set -euo pipefail

# Post-Deployment Configuration Script
# This script runs on each VM to setup the environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${1:-${SCRIPT_DIR}/config.yaml}"
HOSTS_FILE="${2:-${SCRIPT_DIR}/hosts.txt}"
LOG_DIR="${SCRIPT_DIR}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/post_deploy_${TIMESTAMP}.log"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Array to track failed commands
declare -a FAILED_COMMANDS

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1" | tee -a "$LOG_FILE"
}

# Execute command on remote VM, capturing errors but continuing
execute_remote() {
    local vm_ip="$1"
    local username="$2"
    local command="$3"
    local description="$4"
    
    log_info "[$vm_ip] $description"
    log_debug "[$vm_ip] Executing: $command"
    
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 "${username}@${vm_ip}" "$command" >> "$LOG_FILE" 2>&1; then
        log_info "[$vm_ip] ✓ $description succeeded"
        return 0
    else
        log_error "[$vm_ip] ✗ $description failed"
        FAILED_COMMANDS+=("[$vm_ip] $description")
        return 1
    fi
}

# Setup VM environment
setup_vm() {
    local vm_name="$1"
    local vm_ip="$2"
    local username="$3"
    
    log_info "===== Setting up VM: $vm_name ($vm_ip) ====="
    
    # Wait for VM to be accessible
    log_info "[$vm_ip] Waiting for SSH to be available..."
    local max_retries=30
    local retry_count=0
    while ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${username}@${vm_ip}" "echo 'SSH is ready'" &>/dev/null; do
        retry_count=$((retry_count + 1))
        if [ $retry_count -ge $max_retries ]; then
            log_error "[$vm_ip] SSH connection timeout after $max_retries attempts"
            FAILED_COMMANDS+=("[$vm_ip] SSH connection")
            return 1
        fi
        log_info "[$vm_ip] Waiting for SSH... (attempt $retry_count/$max_retries)"
        sleep 10
    done
    log_info "[$vm_ip] SSH is ready"
    
    # Update system packages
    execute_remote "$vm_ip" "$username" \
        "sudo apt-get update -qq" \
        "Updating package lists"
    
    # Install basic dependencies
    execute_remote "$vm_ip" "$username" \
        "sudo apt-get install -y -qq git curl wget ca-certificates gnupg lsb-release" \
        "Installing basic dependencies"
    
    # Check and install Docker
    log_info "[$vm_ip] Checking Docker installation..."
    if ! execute_remote "$vm_ip" "$username" "docker --version" "Checking Docker version"; then
        log_info "[$vm_ip] Installing Docker..."
        execute_remote "$vm_ip" "$username" \
            "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sudo sh /tmp/get-docker.sh" \
            "Installing Docker"
        
        execute_remote "$vm_ip" "$username" \
            "sudo usermod -aG docker ${username}" \
            "Adding user to docker group"
        
        execute_remote "$vm_ip" "$username" \
            "sudo systemctl enable docker && sudo systemctl start docker" \
            "Enabling and starting Docker service"
    else
        log_info "[$vm_ip] Docker is already installed"
    fi
    
    # Check Python version
    log_info "[$vm_ip] Checking Python installation..."
    REQUIRED_PYTHON=$(yq eval '.postDeploy.pythonVersion' "$CONFIG_FILE")
    
    if execute_remote "$vm_ip" "$username" "python3 --version" "Checking Python version"; then
        PYTHON_VERSION=$(ssh -o StrictHostKeyChecking=no "${username}@${vm_ip}" "python3 --version 2>&1 | awk '{print \$2}'")
        log_info "[$vm_ip] Python version: $PYTHON_VERSION"
        
        # Compare versions (basic comparison)
        if execute_remote "$vm_ip" "$username" \
            "python3 -c \"import sys; sys.exit(0 if sys.version_info >= tuple(map(int, '${REQUIRED_PYTHON}'.split('.'))) else 1)\"" \
            "Validating Python version >= ${REQUIRED_PYTHON}"; then
            log_info "[$vm_ip] Python version meets requirements"
        else
            log_warn "[$vm_ip] Python version may not meet requirements (required: ${REQUIRED_PYTHON})"
        fi
    else
        log_warn "[$vm_ip] Python3 not found, attempting to install..."
        execute_remote "$vm_ip" "$username" \
            "sudo apt-get install -y python3 python3-pip python3-venv" \
            "Installing Python3"
    fi
    
    # Check NVIDIA driver and nvidia-smi
    log_info "[$vm_ip] Checking NVIDIA driver and nvidia-smi..."
    if ! execute_remote "$vm_ip" "$username" "nvidia-smi" "Checking nvidia-smi"; then
        log_warn "[$vm_ip] nvidia-smi not available. Installing NVIDIA drivers..."
        
        # Install NVIDIA drivers
        execute_remote "$vm_ip" "$username" \
            "sudo apt-get install -y linux-headers-\$(uname -r)" \
            "Installing kernel headers"
        
        execute_remote "$vm_ip" "$username" \
            "distribution=\$(. /etc/os-release;echo \$ID\$VERSION_ID | sed -e 's/\\.//g') && wget https://developer.download.nvidia.com/compute/cuda/repos/\$distribution/x86_64/cuda-keyring_1.0-1_all.deb && sudo dpkg -i cuda-keyring_1.0-1_all.deb && sudo apt-get update && sudo apt-get -y install cuda-drivers" \
            "Installing NVIDIA drivers"
        
        log_info "[$vm_ip] NVIDIA drivers installed. System may need reboot."
    else
        log_info "[$vm_ip] nvidia-smi is available"
    fi
    
    # Install NVIDIA Container Toolkit for Docker
    log_info "[$vm_ip] Installing NVIDIA Container Toolkit..."
    execute_remote "$vm_ip" "$username" \
        "distribution=\$(. /etc/os-release;echo \$ID\$VERSION_ID) && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg && curl -s -L https://nvidia.github.io/libnvidia-container/\$distribution/libnvidia-container.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list" \
        "Adding NVIDIA Container Toolkit repository"
    
    execute_remote "$vm_ip" "$username" \
        "sudo apt-get update -qq && sudo apt-get install -y nvidia-container-toolkit" \
        "Installing NVIDIA Container Toolkit"
    
    execute_remote "$vm_ip" "$username" \
        "sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker" \
        "Configuring Docker for NVIDIA runtime"
    
    # Clone GitHub repository
    GITHUB_REPO=$(yq eval '.postDeploy.githubRepo' "$CONFIG_FILE")
    REPO_TARGET_DIR=$(yq eval '.postDeploy.repoTargetDir' "$CONFIG_FILE")
    
    log_info "[$vm_ip] Cloning repository: $GITHUB_REPO"
    execute_remote "$vm_ip" "$username" \
        "rm -rf ${REPO_TARGET_DIR} && git clone ${GITHUB_REPO} ${REPO_TARGET_DIR}" \
        "Cloning GitHub repository"
    
    execute_remote "$vm_ip" "$username" \
        "sudo chown -R ${username}:${username} ${REPO_TARGET_DIR}" \
        "Setting repository permissions"
    
    # Pull Docker images
    log_info "[$vm_ip] Pulling Docker images..."
    DOCKER_IMAGES_COUNT=$(yq eval '.postDeploy.dockerImages | length' "$CONFIG_FILE")
    
    for idx in $(seq 0 $((DOCKER_IMAGES_COUNT - 1))); do
        IMAGE=$(yq eval ".postDeploy.dockerImages[$idx]" "$CONFIG_FILE")
        if [[ "$IMAGE" != "null" ]]; then
            execute_remote "$vm_ip" "$username" \
                "docker pull ${IMAGE}" \
                "Pulling Docker image: $IMAGE"
        fi
    done
    
    # Run custom commands if any
    CUSTOM_COMMANDS_COUNT=$(yq eval '.postDeploy.customCommands | length' "$CONFIG_FILE")
    if [[ "$CUSTOM_COMMANDS_COUNT" -gt 0 ]]; then
        log_info "[$vm_ip] Running custom commands..."
        for idx in $(seq 0 $((CUSTOM_COMMANDS_COUNT - 1))); do
            CUSTOM_CMD=$(yq eval ".postDeploy.customCommands[$idx]" "$CONFIG_FILE")
            if [[ "$CUSTOM_CMD" != "null" ]]; then
                execute_remote "$vm_ip" "$username" \
                    "$CUSTOM_CMD" \
                    "Custom command: $CUSTOM_CMD"
            fi
        done
    fi
    
    log_info "[$vm_ip] VM setup completed"
    echo "" | tee -a "$LOG_FILE"
}

# Main execution
main() {
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    log_info "===== Starting Post-Deployment Configuration ====="
    log_info "Configuration file: $CONFIG_FILE"
    log_info "Hosts file: $HOSTS_FILE"
    log_info "Log file: $LOG_FILE"
    log_info ""
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    if [[ ! -f "$HOSTS_FILE" ]]; then
        log_error "Hosts file not found: $HOSTS_FILE"
        exit 1
    fi
    
    # Check for yq
    if ! command -v yq &> /dev/null; then
        log_error "yq is not installed. Please install it from https://github.com/mikefarah/yq"
        exit 1
    fi
    
    # Get admin username from config
    ADMIN_USERNAME=$(yq eval '.vm.adminUsername' "$CONFIG_FILE")
    
    # Process each VM in the hosts file
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            VM_NAME=$(echo "$line" | awk '{print $1}')
            PUBLIC_IP=$(echo "$line" | awk '{print $2}')
            PRIVATE_IP=$(echo "$line" | awk '{print $3}')
            
            setup_vm "$VM_NAME" "$PUBLIC_IP" "$ADMIN_USERNAME"
        fi
    done < "$HOSTS_FILE"
    
    # Summary
    log_info ""
    log_info "===== Post-Deployment Summary ====="
    
    if [ ${#FAILED_COMMANDS[@]} -eq 0 ]; then
        log_info "✓ All commands executed successfully!"
    else
        log_warn "⚠ Some commands failed:"
        for failed_cmd in "${FAILED_COMMANDS[@]}"; do
            log_error "  - $failed_cmd"
        done
        log_info ""
        log_info "Please review the log file for details: $LOG_FILE"
        exit 1
    fi
    
    log_info ""
    log_info "Post-deployment configuration completed!"
    log_info "Log file: $LOG_FILE"
}

main "$@"
