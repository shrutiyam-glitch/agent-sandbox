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

# enable autoscaling 
# enable NAP - Node auto provisioning
gcloud container clusters create ${CLUSTER} \
  --location ${REGION} \
  --release-channel rapid \
  --cluster-version ${CLUSTER_VERSION} \
  --workload-pool="${PROJECT_ID}.svc.id.goog" \
  --workload-metadata=GKE_METADATA \
  --enable-image-streaming \
  --enable-autoscaling \
  --enable-autoprovisioning --max-cpu 1000000 --max-memory 1000000 \
  --num-nodes 1 \
  --monitoring=SYSTEM


# Agent sandbox set up  
export IMAGE_PREFIX="us-central1-docker.pkg.dev/shrutiyam-gke-dev/agent-sandbox-repo/"
./dev/tools/push-images --image-prefix=${IMAGE_PREFIX} --controller-only
./dev/tools/deploy-to-kube --image-prefix=${IMAGE_PREFIX}

# Create sandbox namespace
kubectl create namespace sandbox-test

# Create sandbox template
kubectl apply -f python-sandbox-template.yaml

# Create sandbox warmpool
kubectl apply -f sandboxwarmpool.yaml

# Capacity Buffer 
# Apply RBAC permissions 
kubectl apply -f rbac.yaml

# Create capacity buffer 
kubectl apply -f capacitybuffer.yaml

# HPA 
# Enable podmonitoring in agent-sandbox-system namespace to extract the metrics to cloud monitoring 
kubectl apply -f pod_monitoring.yaml

# Enable custom metrics adapter for HPA to consume the external metrics from Prometheus

kubectl create clusterrolebinding cluster-admin-binding \
    --clusterrole cluster-admin --user "$(gcloud config get-value account)"

kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-stackdriver/master/custom-metrics-stackdriver-adapter/deploy/production/adapter_new_resource_model.yaml

gcloud projects add-iam-policy-binding projects/${PROJECT_ID} \
  --role roles/monitoring.viewer \
  --member=principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/custom-metrics/sa/custom-metrics-stackdriver-adapter

# Apply sandboxclaim to trigger the metrics in the agent-sandbox-controller 
kubectl apply -f sandboxclaim.yaml

# Apply HPA 
kubectl apply -f hpa_prometheus.yaml



