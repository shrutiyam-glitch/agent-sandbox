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

export CLOUDSDK_API_ENDPOINT_OVERRIDES_CONTAINER="https://staging-container.mtls.sandbox.googleapis.com/"
export CLUSTER_NAME="baseline-test-cluster"
export REGION="us-central1"
export PROJECT_ID="shrutiyam-gke-dev"

gcloud container clusters create ${CLUSTER_NAME} \
    --region ${REGION} \
    --machine-type e2-standard-32 \
    --num-nodes 17 \
    --workload-pool="${PROJECT_ID}.svc.id.goog" \
    --enable-image-streaming \
    --monitoring=SYSTEM

kubectl apply -f release_assets/manifest.yaml
kubectl apply -f release_assets/extensions.yaml

# comment out the capacity buffer and hpa sections in the rapid-burst-test.yaml file

cd dev/load-test/test-recipes/
./run_rapid_burst.sh
