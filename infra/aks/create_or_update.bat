@echo off
setlocal enabledelayedexpansion

set "RESOURCE_GROUP="
set "LOCATION="
set "CLUSTER_NAME="
set "SSH_KEY="
set "K8S_VERSION="
set "PARAMS="

:parse_args
if "%~1"=="" goto validate_args
if "%~1"=="--resource-group" (
    set "RESOURCE_GROUP=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--location" (
    set "LOCATION=%~2"
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
if "%~1"=="--ssh-public-key" (
    set "SSH_KEY=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--k8s-version" (
    set "K8S_VERSION=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--param" (
    if "!PARAMS!"=="" (
        set "PARAMS=%~2"
    ) else (
        set "PARAMS=!PARAMS! %~2"
    )
    shift
    shift
    goto parse_args
)
echo Unknown argument: %~1 1>&2
exit /b 1

:validate_args
if "%RESOURCE_GROUP%"=="" (
    echo Usage: %~nx0 --resource-group ^<rg^> --location ^<region^> --cluster-name ^<name^> --ssh-public-key ^<path^> [--k8s-version ^<ver^>] 1>&2
    exit /b 1
)
if "%LOCATION%"=="" (
    echo Usage: %~nx0 --resource-group ^<rg^> --location ^<region^> --cluster-name ^<name^> --ssh-public-key ^<path^> [--k8s-version ^<ver^>] 1>&2
    exit /b 1
)
if "%CLUSTER_NAME%"=="" (
    echo Usage: %~nx0 --resource-group ^<rg^> --location ^<region^> --cluster-name ^<name^> --ssh-public-key ^<path^> [--k8s-version ^<ver^>] 1>&2
    exit /b 1
)
if "%SSH_KEY%"=="" (
    echo Usage: %~nx0 --resource-group ^<rg^> --location ^<region^> --cluster-name ^<name^> --ssh-public-key ^<path^> [--k8s-version ^<ver^>] 1>&2
    exit /b 1
)

if not exist "%SSH_KEY%" (
    echo SSH public key not found: %SSH_KEY% 1>&2
    exit /b 1
)

REM Create resource group
az group create --name "%RESOURCE_GROUP%" --location "%LOCATION%"
if %errorlevel% neq 0 exit /b %errorlevel%

REM Create temporary parameter file
set "temp_param_file=%TEMP%\aks_params_%RANDOM%.json"

REM Read SSH key content
set "ssh_key_content="
for /f "usebackq delims=" %%i in ("%SSH_KEY%") do set "ssh_key_content=%%i"

REM Create parameter file based on whether K8S version is provided
if "%K8S_VERSION%"=="" (
    (
        echo {
        echo   "clusterName": {"value": "%CLUSTER_NAME%"},
        echo   "location": {"value": "%LOCATION%"},
        echo   "sshRSAPublicKey": {"value": "%ssh_key_content%"}
        echo }
    ) > "%temp_param_file%"
) else (
    (
        echo {
        echo   "clusterName": {"value": "%CLUSTER_NAME%"},
        echo   "location": {"value": "%LOCATION%"},
        echo   "sshRSAPublicKey": {"value": "%ssh_key_content%"},
        echo   "kubernetesVersion": {"value": "%K8S_VERSION%"}
        echo }
    ) > "%temp_param_file%"
)

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

echo Deploying AKS cluster...
if "%PARAMS%"=="" (
    az deployment group create --resource-group "%RESOURCE_GROUP%" --name "%CLUSTER_NAME%-deployment" --template-file "%SCRIPT_DIR%main.bicep" --parameters "@%temp_param_file%"
) else (
    az deployment group create --resource-group "%RESOURCE_GROUP%" --name "%CLUSTER_NAME%-deployment" --template-file "%SCRIPT_DIR%main.bicep" --parameters "@%temp_param_file%" %PARAMS%
)
if %errorlevel% neq 0 (
    del "%temp_param_file%" 2>nul
    exit /b %errorlevel%
)

REM Clean up temporary file
del "%temp_param_file%" 2>nul

echo Fetching cluster credentials...
az aks get-credentials --resource-group "%RESOURCE_GROUP%" --name "%CLUSTER_NAME%" --overwrite-existing
if %errorlevel% neq 0 exit /b %errorlevel%

echo Creating namespaces and labels...
kubectl create namespace nc40adis --dry-run=client -o yaml | kubectl apply -f -
if %errorlevel% neq 0 exit /b %errorlevel%
kubectl label namespace nc40adis workload=nc40adis --overwrite
if %errorlevel% neq 0 exit /b %errorlevel%

kubectl create namespace nc80adis --dry-run=client -o yaml | kubectl apply -f -
if %errorlevel% neq 0 exit /b %errorlevel%
kubectl label namespace nc80adis workload=nc80adis --overwrite
if %errorlevel% neq 0 exit /b %errorlevel%

echo Cluster ready: %CLUSTER_NAME%
exit /b 0
