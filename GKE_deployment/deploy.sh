#!/bin/bash
set -e

# Usage: ./deploy.sh <PROJECT_ID> <IMAGE_NAME> <REGION>
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <PROJECT_ID> <IMAGE_NAME> <REGION>"
    echo "Example: $0 my-project us-central1-docker.pkg.dev/my-project/repo/ecofood:latest us-central1"
    exit 1
fi

PROJECT_ID=$1
IMAGE_NAME=$2
REGION=$3

echo "========================================================"
echo "Deploying EcoFood to GKE"
echo "Project: $PROJECT_ID"
echo "Image:   $IMAGE_NAME"
echo "Region:  $REGION"
echo "========================================================"

# 1. Build Docker Image
echo "[1/4] Building Docker image..."
docker build -f backend/Dockerfile -t $IMAGE_NAME .

# 2. Push to Artifact Registry
echo "[2/4] Pushing image to registry..."
docker push $IMAGE_NAME

# 3. Connect to Cluster (Optional - ensures kubectl context is set)
# echo "Connecting to cluster..."
# gcloud container clusters get-credentials <CLUSTER_NAME> --region $REGION --project $PROJECT_ID

# 4. Apply Manifests
echo "[3/4] Applying Kubernetes manifests..."

# Apply Namespace & Secrets first
kubectl apply -f GKE_deployment/namespace.yaml
kubectl apply -f GKE_deployment/secrets.yaml

# Apply Database & Langfuse
kubectl apply -f GKE_deployment/postgres.yaml
kubectl apply -f GKE_deployment/langfuse.yaml

# Apply App (with envsubst for Image Name)
echo "[4/4] Deploying App..."
export IMAGE_NAME=$IMAGE_NAME
envsubst < GKE_deployment/app.yaml | kubectl apply -f -

echo "========================================================"
echo "Deployment Complete!"
echo "Check status: kubectl get pods -n ecofood"
echo "========================================================"
