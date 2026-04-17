export PROJECT_ID=$(gcloud config get project) #use the current project set in gcloud
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")


export CLUSTER=cb-hpa-new-cluster #hpa-ps-cluster #change cluster name
export REGION=us-central1 #change region
export NODE_LOCATIONS=${REGION}-c
export NODE_POOL=cb-hpa-nodepool
export NODE_VERSION=1.35.2-gke.1842001 #1.35.1-gke.1396001
export MACHINE_TYPE=c4-standard-16


export NAMESPACE=sandbox-test
export BUCKET_NAME=${PROJECT_ID}-snapshots
export FOLDER_PATH=${CLUSTER}/${NAMESPACE}
export CLUSTER_VERSION=1.35.2-gke.1842001 #1.35.1-gke.1396001
export KSA_NAME=sandbox-test


# export REGISTRY=gcr.io/gke-release
# export GPS_VERSION=v1.0-1