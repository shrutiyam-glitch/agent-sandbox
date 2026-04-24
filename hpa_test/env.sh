# Copyright 2026 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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