# EcoFood GKE Deployment

This directory contains Kubernetes manifests and scripts to deploy the EcoFood application to Google Kubernetes Engine (GKE).

## Prerequisites

1.  **Google Cloud Project**: You need an active GCP project.
2.  **GKE Cluster**: A running Kubernetes cluster on GKE.
3.  **Artifact Registry**: A Docker repository in Google Artifact Registry (GAR) to store the application image.
4.  **Tools**:
    -   `gcloud` CLI (authenticated)
    -   `kubectl` (configured to talk to your cluster)
    -   `docker` (authenticated with GAR)

## Directory Structure

-   `deploy.sh`: Automated deployment script.
-   `namespace.yaml`: Creates the `ecofood` namespace.
-   `secrets.yaml`: Placeholder for secrets (API keys, passwords). **Update this before deploying!**
-   `postgres.yaml`: Database deployment (StatefulSet).
-   `langfuse.yaml`: Langfuse observability platform (Deployment + DB).
-   `app.yaml`: Main EcoFood application (Deployment + Service).

## How to Deploy

1.  **Configure Secrets**:
    Edit `secrets.yaml` and replace the placeholder values (base64 encoded) with your actual secrets:
    -   `GEMINI_API_KEY`
    -   `POSTGRES_PASSWORD`
    -   `LANGFUSE_SECRET_KEY`
    -   etc.

2.  **Run Deployment Script**:
    Run the `deploy.sh` script with your Project ID, Image Name (full path to GAR), and Region.

    ```bash
    ./deploy.sh <PROJECT_ID> <IMAGE_NAME> <REGION>
    ```

    **Example**:
    ```bash
    ./deploy.sh my-gcp-project us-central1-docker.pkg.dev/my-gcp-project/my-repo/ecofood:latest us-central1
    ```

    The script will:
    -   Build the Docker image.
    -   Push it to the specified registry.
    -   Apply all Kubernetes manifests to the cluster.

3.  **Access the Application**:
    -   Get the external IP (if using LoadBalancer) or port-forward:
        ```bash
        kubectl port-forward svc/ecofood-app 3000:3000 -n ecofood
        ```
    -   Open `http://localhost:3000`.
