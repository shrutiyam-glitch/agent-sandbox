export CLOUDSDK_API_ENDPOINT_OVERRIDES_CONTAINER="https://staging-container.mtls.sandbox.googleapis.com/"
export CLUSTER_NAME="cb-hpa-test-cluster"
export REGION="us-central1"
export PROJECT_ID="shrutiyam-gke-dev"
export CLUSTER_VERSION="1.35.2-gke.1842002" #"1.35.2-gke.1842002"

export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

gcloud container clusters create ${CLUSTER_NAME} \
  --location ${REGION} \
  --machine-type e2-standard-32 \
  --release-channel None \
  --no-enable-autoupgrade \
  --cluster-version ${CLUSTER_VERSION} \
  --workload-pool="${PROJECT_ID}.svc.id.goog" \
  --enable-image-streaming \
  --enable-autoscaling \
  --enable-autoprovisioning --max-cpu 1000000 --max-memory 1000000 \
  --num-nodes 1 \
  --monitoring=SYSTEM



# Apply maintenance exclusion to prevent any upgrades
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Set end time for a duration sufficient for your testing (e.g., 7 days)
END_TIME=$(date -u -d "+30 days" +"%Y-%m-%dT%H:%M:%SZ")

gcloud container clusters update ${CLUSTER_NAME} \
    --location ${REGION} \
    --add-maintenance-exclusion-name "upgrade-hold" \
    --add-maintenance-exclusion-start "${START_TIME}" \
    --add-maintenance-exclusion-end "${END_TIME}" \
    --add-maintenance-exclusion-scope "no_upgrades"


kubectl apply -f release_assets/manifest.yaml
kubectl apply -f release_assets/extensions.yaml

cd dev/load-test/test-recipes/cb-hpa
# Apply podmonitoring
kubectl apply -f pod_monitoring.yaml
# Apply rbac for the capacity buffer to access the swp
kubectl apply -f rbac.yaml


# Enable custom metrics adapter for HPA to consume the external metrics from Prometheus

kubectl create clusterrolebinding cluster-admin-binding \
    --clusterrole cluster-admin --user "$(gcloud config get-value account)"

kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-stackdriver/master/custom-metrics-stackdriver-adapter/deploy/production/adapter_new_resource_model.yaml

gcloud projects add-iam-policy-binding projects/${PROJECT_ID} \
  --role roles/monitoring.viewer \
  --member=principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/custom-metrics/sa/custom-metrics-stackdriver-adapter

cd ..
# uncomment the capacity buffer and hpa sections in the rapid-burst-test.yaml file
./run_rapid_burst.sh cb-hpa-test-1





######


gcloud container clusters describe hpa-cb-new-test-cluster \
    --location us-central1 \
    --format="value(id)"
