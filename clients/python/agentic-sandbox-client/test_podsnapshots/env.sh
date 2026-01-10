export PROJECT_ID=$(gcloud config get project) #use the current project set in gcloud
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Cluster / Node Pool Variables FILL IN BELOW with your own custom values

export CLUSTER=pss-pysdk-cluster #change cluster name
export REGION=us-central1 #change region
export NODE_LOCATIONS=${REGION}-c

# Snapshot specific variables

export NAMESPACE=sandbox-test
export BUCKET_NAME=${PROJECT_ID}-snapshots
export FOLDER_PATH=${CLUSTER}/${NAMESPACE}
export CLUSTER_VERSION=1.34.1-gke.2037000
export KSA_NAME=sandbox-test


export REGISTRY=gcr.io/gke-release
export GPS_VERSION=v1.0-1


export AGENT_SANDBOX_VERSION="v0.1.0"

# pip install --index-url https://pypi.org/simple/ -e .
