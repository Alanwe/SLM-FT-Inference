param clusterName string
param location string
param kubernetesVersion string = '1.29.2'
param sshRSAPublicKey string
param adminUsername string = 'azureuser'
param tags object = {
  environment: 'demo'
  project: 'azure-nc-llm'
}

var systemNodePool = {
  name: 'systempool'
  vmSize: 'Standard_D8s_v5'
  osType: 'Linux'
  osDiskSizeGB: 128
  type: 'VirtualMachineScaleSets'
  mode: 'System'
  enableAutoScaling: true
  minCount: 1
  maxCount: 3
}

resource aks 'Microsoft.ContainerService/managedClusters@2024-04-01' = {
  name: clusterName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    dnsPrefix: '${clusterName}-dns'
    kubernetesVersion: kubernetesVersion
    enableRBAC: true
    nodeResourceGroup: '${clusterName}-nodes'
    apiServerAccessProfile: {
      enablePrivateCluster: false
    }
    agentPoolProfiles: [
      {
        name: systemNodePool.name
        count: 1
        vmSize: systemNodePool.vmSize
        osType: systemNodePool.osType
        osDiskSizeGB: systemNodePool.osDiskSizeGB
        type: systemNodePool.type
        mode: systemNodePool.mode
        enableAutoScaling: systemNodePool.enableAutoScaling
        minCount: systemNodePool.minCount
        maxCount: systemNodePool.maxCount
      }
      {
        name: 'nc40adis'
        count: 0
        vmSize: 'Standard_NC40adis_H100_v5'
        osType: 'Linux'
        osDiskSizeGB: 256
        type: 'VirtualMachineScaleSets'
        mode: 'User'
        enableAutoScaling: true
        minCount: 0
        maxCount: 10
        nodeTaints: [
          'sku=nc40adis:NoSchedule'
        ]
        scaleSetPriority: 'Spot'
        scaleSetEvictionPolicy: 'Delete'
        spotMaxPrice: -1
      }
      {
        name: 'nc80adis'
        count: 0
        vmSize: 'Standard_NC80adis_H100_v5'
        osType: 'Linux'
        osDiskSizeGB: 512
        type: 'VirtualMachineScaleSets'
        mode: 'User'
        enableAutoScaling: true
        minCount: 0
        maxCount: 10
        nodeTaints: [
          'sku=nc80adis:NoSchedule'
        ]
        scaleSetPriority: 'Spot'
        scaleSetEvictionPolicy: 'Delete'
        spotMaxPrice: -1
      }
    ]
    linuxProfile: {
      adminUsername: adminUsername
      ssh: {
        publicKeys: [
          {
            keyData: sshRSAPublicKey
          }
        ]
      }
    }
    networkProfile: {
      networkPlugin: 'azure'
      networkPolicy: 'azure'
      loadBalancerSku: 'standard'
      outboundType: 'loadBalancer'
    }
  }
}

output kubeletIdentity object = aks.properties.identityProfile.kubeletidentity
