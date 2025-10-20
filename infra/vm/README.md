# Azure VM Infrastructure for ML Workloads

This directory contains scripts and configuration for creating and managing Azure Virtual Machines optimized for machine learning workloads with GPU support.

## Overview

The VM infrastructure automation includes:
- **Configurable VM creation** - Deploy multiple VMs with specified SKU types
- **Flexible configuration** - Support for Standard or Spot (low-priority) VMs
- **Automated post-deployment** - Setup Docker, Python, NVIDIA drivers, and clone repositories
- **Network management** - Automated VNet, subnet, and NSG creation
- **Error handling** - Continue on errors and report failed commands
- **Hosts file generation** - Automatic inventory of created VM IP addresses

## Prerequisites

1. **Azure CLI** (version 2.63+)
   ```bash
   # Install Azure CLI
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   
   # Login to Azure
   az login
   ```

2. **yq** (YAML processor)
   ```bash
   # Linux
   sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
   sudo chmod +x /usr/local/bin/yq
   
   # macOS
   brew install yq
   ```

3. **SSH Key Pair**
   ```bash
   # Generate SSH key if you don't have one
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
   ```

## Quick Start

1. **Configure your deployment**
   
   Edit `config.yaml` to specify:
   - Number of VMs to create
   - VM size/SKU (e.g., Standard_NC6s_v3, Standard_NC40adis_H100_v5)
   - Priority (Standard or Spot)
   - Resource group and location
   - Network settings
   - Post-deployment tasks

2. **Create VMs**
   
   ```bash
   chmod +x create_vms.sh
   ./create_vms.sh
   ```
   
   This will:
   - Create the resource group
   - Set up networking (VNet, subnet, NSG)
   - Create the specified number of VMs
   - Generate `hosts.txt` with VM IP addresses
   - Run post-deployment configuration

3. **Check VM status**
   
   ```bash
   ./check_status.sh
   ```
   
   This will show:
   - VM power states and sizes
   - SSH connectivity status
   - Docker installation status
   - GPU availability (nvidia-smi output)
   - Cost estimates

4. **Access your VMs**
   
   ```bash
   # View created VMs and their IPs
   cat hosts.txt
   
   # SSH into a VM
   ssh azureuser@<public-ip>
   ```

5. **Destroy infrastructure**
   
   ```bash
   chmod +x destroy_vms.sh
   ./destroy_vms.sh
   ```

## Configuration File

The `config.yaml` file contains all deployment parameters:

### VM Configuration
```yaml
vm:
  count: 2                          # Number of VMs to create
  vmSize: "Standard_NC6s_v3"        # Azure VM SKU
  namePrefix: "slm-vm"              # VM name prefix (will add index)
  priority: "Standard"              # Standard or Spot
  evictionPolicy: "Deallocate"      # For Spot VMs: Deallocate or Delete
  maxPrice: -1                      # Max price for Spot (-1 = on-demand price)
```

### Common VM SKUs

**GPU VMs (V100)**
- `Standard_NC6s_v3` - 1x V100, 6 vCPU, 112 GB RAM
- `Standard_NC12s_v3` - 2x V100, 12 vCPU, 224 GB RAM
- `Standard_NC24s_v3` - 4x V100, 24 vCPU, 448 GB RAM

**GPU VMs (H100)**
- `Standard_NC40adis_H100_v5` - 1x H100, 40 vCPU, 320 GB RAM
- `Standard_NC80adis_H100_v5` - 2x H100, 80 vCPU, 640 GB RAM

**GPU VMs (A100)**
- `Standard_NC24ads_A100_v4` - 1x A100, 24 vCPU, 220 GB RAM
- `Standard_NC48ads_A100_v4` - 2x A100, 48 vCPU, 440 GB RAM

### Image Configuration
```yaml
vm:
  image:
    publisher: "Canonical"
    offer: "0001-com-ubuntu-server-jammy"
    sku: "22_04-lts-gen2"
    version: "latest"
```

### Network Configuration
```yaml
network:
  vnetName: "slm-vnet"
  vnetAddressPrefix: "10.0.0.0/16"
  subnetName: "slm-subnet"
  subnetAddressPrefix: "10.0.1.0/24"
  allowedSshSources:
    - "0.0.0.0/0"  # Allow from all IPs (restrict for production)
```

### Post-Deployment Configuration
```yaml
postDeploy:
  githubRepo: "https://github.com/Alanwe/SLM-FT-Inference.git"
  repoTargetDir: "/home/azureuser/SLM-FT-Inference"
  pythonVersion: "3.11"
  dockerImages:
    - "nvidia/cuda:12.2.0-runtime-ubuntu22.04"
    - "huggingface/transformers-pytorch-gpu:latest"
  customCommands: []  # Add custom bash commands here
```

## Post-Deployment Tasks

The `post_deploy.sh` script automatically performs the following on each VM:

1. **System Updates**
   - Update package lists
   - Install basic dependencies (git, curl, wget, etc.)

2. **Docker Installation**
   - Check if Docker is installed
   - Install Docker if missing
   - Add user to docker group
   - Enable and start Docker service

3. **Python Verification**
   - Check Python 3 installation
   - Verify version meets requirements
   - Install Python if missing

4. **NVIDIA Setup**
   - Check for nvidia-smi
   - Install NVIDIA drivers if missing
   - Install NVIDIA Container Toolkit
   - Configure Docker for GPU support

5. **Repository Setup**
   - Clone GitHub repository
   - Set proper ownership and permissions

6. **Docker Images**
   - Pull specified Docker images

7. **Custom Commands**
   - Execute any custom commands specified in config

### Error Handling

The post-deployment script:
- Continues execution even if individual commands fail
- Logs all output to `logs/post_deploy_<timestamp>.log`
- Maintains a list of failed commands
- Provides a summary report at the end

## Files Generated

- **hosts.txt** - List of VMs with public and private IPs
  ```
  slm-vm-1 20.12.34.56 10.0.1.4
  slm-vm-2 20.12.34.57 10.0.1.5
  ```

- **logs/post_deploy_<timestamp>.log** - Detailed post-deployment logs

## Scripts

### create_vms.sh

Main script to create VM infrastructure.

**Usage:**
```bash
./create_vms.sh [--config <config-file>]
```

**Options:**
- `--config <file>` - Use custom configuration file (default: config.yaml)
- `--help, -h` - Show help message

### post_deploy.sh

Post-deployment configuration script (automatically called by create_vms.sh).

**Usage:**
```bash
./post_deploy.sh <config-file> <hosts-file>
```

### check_status.sh

Check the status of created VMs, test connectivity, and view GPU/Docker status.

**Usage:**
```bash
./check_status.sh [--config <config-file>]
```

**Options:**
- `--config <file>` - Use custom configuration file (default: config.yaml)
- `--help, -h` - Show help message

**Features:**
- Lists all VMs and their power states
- Tests SSH connectivity to each VM
- Checks Docker installation status
- Reports GPU status via nvidia-smi
- Provides cost estimates

### destroy_vms.sh

Destroy all created resources.

**Usage:**
```bash
./destroy_vms.sh [--config <config-file>] [--force]
```

**Options:**
- `--config <file>` - Use custom configuration file
- `--force` - Skip confirmation prompt
- `--help, -h` - Show help message

## Advanced Usage

### Using Spot VMs

To use low-priority Spot VMs for cost savings:

```yaml
vm:
  priority: "Spot"
  evictionPolicy: "Deallocate"  # or "Delete"
  maxPrice: -1  # Pay up to on-demand price
```

### Custom Post-Deployment Commands

Add custom commands to run after the standard setup:

```yaml
postDeploy:
  customCommands:
    - "pip install -r /home/azureuser/SLM-FT-Inference/requirements.txt"
    - "sudo apt-get install -y htop nvtop"
```

### Multiple Environments

Use different configuration files for different environments:

```bash
# Development environment
./create_vms.sh --config config.dev.yaml

# Production environment
./create_vms.sh --config config.prod.yaml
```

## Troubleshooting

### SSH Connection Issues

If you can't connect to VMs:
1. Check NSG rules allow SSH from your IP
2. Verify VM is running: `az vm list -g <resource-group> -o table`
3. Check public IP: `az network public-ip show -g <resource-group> -n <vm-name>-ip`

### Post-Deployment Failures

Check the detailed log file:
```bash
cat logs/post_deploy_<timestamp>.log
```

Re-run post-deployment manually:
```bash
./post_deploy.sh config.yaml hosts.txt
```

### GPU Not Available

If `nvidia-smi` fails:
1. Ensure you're using a GPU-enabled VM SKU
2. Check NVIDIA driver installation logs
3. May need to reboot VM after driver installation
4. Verify GPU availability: `lspci | grep -i nvidia`

### Quota Limits

If VM creation fails due to quota:
1. Check your subscription quota: `az vm list-usage -l <location> -o table`
2. Request quota increase through Azure Portal
3. Try a different region or VM size

## Cost Optimization

1. **Use Spot VMs** - Save up to 90% compared to on-demand pricing
2. **Scale down when not in use** - Deallocate VMs when idle
3. **Use appropriate VM sizes** - Don't over-provision resources
4. **Set up auto-shutdown** - Configure automatic shutdown schedules
5. **Monitor usage** - Use Azure Cost Management to track spending

## Security Best Practices

1. **Restrict SSH access** - Limit `allowedSshSources` to your IP range
2. **Use strong SSH keys** - Generate 4096-bit RSA keys
3. **Enable Azure Security Center** - Monitor for security threats
4. **Regular updates** - Keep VMs and software up to date
5. **Use Azure Key Vault** - Store sensitive credentials securely
6. **Enable disk encryption** - Encrypt OS and data disks

## Next Steps

After VM creation:
1. Verify all services are running: `ssh azureuser@<ip> "docker ps; nvidia-smi"`
2. Test GPU functionality: `ssh azureuser@<ip> "docker run --rm --gpus all nvidia/cuda:12.2.0-base nvidia-smi"`
3. Clone and setup your workload
4. Configure distributed training if using multiple VMs

## Support

For issues and questions:
- Check Azure VM documentation: https://docs.microsoft.com/azure/virtual-machines/
- Review NVIDIA driver installation guides
- Check GitHub repository issues

## License

This infrastructure code is provided for demonstration purposes. Customize as needed for your workloads.
