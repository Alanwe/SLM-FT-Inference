@echo off
setlocal enabledelayedexpansion

set "RESOURCE_GROUP="
set "CLUSTER_NAME="
set "DELETE_RG=false"

:parse_args
if "%~1"=="" goto validate_args
if "%~1"=="--resource-group" (
    set "RESOURCE_GROUP=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--cluster-name" (
    set "CLUSTER_NAME=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--delete-resource-group" (
    set "DELETE_RG=true"
    shift
    goto parse_args
)
echo Unknown argument: %~1 1>&2
exit /b 1

:validate_args
if "%RESOURCE_GROUP%"=="" (
    echo Usage: %~nx0 --resource-group ^<rg^> --cluster-name ^<name^> [--delete-resource-group] 1>&2
    exit /b 1
)
if "%CLUSTER_NAME%"=="" (
    echo Usage: %~nx0 --resource-group ^<rg^> --cluster-name ^<name^> [--delete-resource-group] 1>&2
    exit /b 1
)

echo Deleting AKS cluster %CLUSTER_NAME%...
az aks delete --name "%CLUSTER_NAME%" --resource-group "%RESOURCE_GROUP%" --yes --no-wait

REM Get subscription ID
for /f "usebackq tokens=*" %%i in (`az account show --query id -o tsv`) do set "SUBSCRIPTION_ID=%%i"

echo Waiting for cluster deletion to finish...
az resource wait --deleted --ids "/subscriptions/%SUBSCRIPTION_ID%/resourceGroups/%RESOURCE_GROUP%/providers/Microsoft.ContainerService/managedClusters/%CLUSTER_NAME%"

if "%DELETE_RG%"=="true" (
    echo Deleting resource group %RESOURCE_GROUP%...
    az group delete --name "%RESOURCE_GROUP%" --yes --no-wait
)

exit /b 0
