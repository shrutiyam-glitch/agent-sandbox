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

# Example: Granting monitoring.viewer to custom-metrics-adapter-sa
SERVICE_ACCOUNT_EMAIL="custom-metrics-adapter-sa@gke-ai-open-models.iam.gserviceaccount.com"
ROLE_TO_GRANT="roles/monitoring.viewer"

gcloud projects add-iam-policy-binding gke-ai-open-models \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="${ROLE_TO_GRANT}"
