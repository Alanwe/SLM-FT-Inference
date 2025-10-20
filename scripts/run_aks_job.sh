#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <namespace> <job-name> <command...>" >&2
  exit 1
fi

NAMESPACE=$1
shift
JOB_NAME=$1
shift

cat <<JOB | kubectl apply -n "$NAMESPACE" -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: trainer
          image: ghcr.io/your-org/azure-nc-llm-demo:latest
          envFrom:
            - secretRef:
                name: training-env
          command: ["uv", "run"]
          args: ["$@"]
          resources:
            limits:
              nvidia.com/gpu: 1
JOB
