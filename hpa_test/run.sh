source env.sh

# Hpa is installed by default in GKE
kubectl api-versions | grep autoscaling
kubectl get apiservice | grep metrics
kubectl get hpa --all-namespaces

gcloud container clusters update ${CLUSTER} \
    --region ${REGION} \
    --autoscaling-profile=optimize-utilization

gcloud container clusters update ${CLUSTER} \
    --region ${REGION} \
    --monitoring=SYSTEM,WORKLOAD

gcloud container clusters update ${CLUSTER} \
    --region ${REGION} \
    --enable-managed-prometheus \
    --monitoring=SYSTEM

gcloud beta container clusters create ${CLUSTER} \
        --project=${PROJECT_ID} \
        --region=${REGION} \
        --cluster-version=${CLUSTER_VERSION} \
        --node-locations=${NODE_LOCATIONS} \
        --workload-pool="${PROJECT_ID}.svc.id.goog" \
        --workload-metadata=GKE_METADATA \
        --enable-pod-snapshots \
        --num-nodes=1 \
        --release-channel=rapid \
        --machine-type=e2-standard-2 \
        --enable-autoscaling \ 
        --min-nodes=1 \
        --max-nodes=3

# enable-autoscaling - for capacity buffer 
# release-channel=rapid - for autoscalingmetric


gcloud beta container node-pools create "${NODE_POOL}" \
        --project="${PROJECT_ID}" \
        --cluster="${CLUSTER}" \
        --region="${REGION}" \
        --node-locations="${NODE_LOCATIONS}" \
        --num-nodes=1 \
        --image-type=cos_containerd \
        --machine-type="${MACHINE_TYPE}" \
        --sandbox=type=gvisor

kubectl create namespace sandbox-test

kubectl create serviceaccount sandbox-test -n sandbox-test

# Install agent-sandbox

kubectl apply -f python-counter-template.yaml

kubectl apply -f sandboxwarmpool.yaml

kubectl apply -f autoscalingmetric.yaml

kubectl apply -f hpa.yaml

gcloud container node-pools update "${NODE_POOL}" \
  --cluster="${CLUSTER}" \
  --region="${REGION}" \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10

# enable controle plane logs 
gcloud container clusters update "${CLUSTER}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --enable-master-logs=APISERVER,SCHEDULER,CONTROLLER_MANAGER


kubectl apply -f capacitybuffer.yaml


#
# HELP agent_sandbox_warmpool_replicas Current number of replicas in the SandboxWarmPool.
# TYPE agent_sandbox_warmpool_replicas gauge
# agent_sandbox_warmpool_replicas{name="python-sdk-warmpool",namespace="default",template_name="python-counter-template"} 2
# agent_sandbox_warmpool_replicas{name="python-sdk-warmpool",namespace="sandbox-test",template_name="python-counter-template"} 2


#stackdriver adaptor
gcloud iam service-accounts create custom-metrics-adapter-sa \
    --display-name="Custom Metrics Adapter Service Account"

gcloud projects add-iam-policy-binding shrutiyam-gke-dev \
    --member="serviceAccount:custom-metrics-adapter-sa@shrutiyam-gke-dev.iam.gserviceaccount.com" \
    --role="roles/monitoring.viewer"

gcloud iam service-accounts add-iam-policy-binding \
    custom-metrics-adapter-sa@shrutiyam-gke-dev.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:shrutiyam-gke-dev.svc.id.goog[custom-metrics/custom-metrics-stackdriver-adapter]"

kubectl annotate serviceaccount custom-metrics-stackdriver-adapter \
    --namespace custom-metrics \
    iam.gke.io/gcp-service-account=custom-metrics-adapter-sa@shrutiyam-gke-dev.iam.gserviceaccount.com

gcloud container clusters update hpa-cb-cluster     --monitoring=SYSTEM,CONTROLLER_MANAGER,POD     --location us-central1


#####################################

gcloud projects add-iam-policy-binding gke-ai-open-models \
    --member="serviceAccount:custom-metrics-adapter-sa@gke-ai-open-models.iam.gserviceaccount.com" \
    --role="roles/monitoring.viewer"

gcloud iam service-accounts add-iam-policy-binding \
    custom-metrics-adapter-sa@gke-ai-open-models.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:gke-ai-open-models.svc.id.goog[custom-metrics/custom-metrics-stackdriver-adapter]"

kubectl annotate serviceaccount custom-metrics-stackdriver-adapter \
    --namespace custom-metrics \
    iam.gke.io/gcp-service-account=custom-metrics-adapter-sa@gke-ai-open-models.iam.gserviceaccount.com




############# CB only #################

# enable autoscaling 
# enable NAP - Node auto provisioning
gcloud container clusters create ${CLUSTER} \
    --location ${REGION} \
    --cluster-version=${CLUSTER_VERSION} \
    --enable-autoscaling --min-nodes 1 --max-nodes 10 \
    --num-nodes 3 \
    --enable-autoprovisioning \
    --autoprovisioning-locations ${NODE_LOCATIONS} \
    --min-cpu 1 \
    --min-memory 1 \
    --max-cpu 100 \
    --max-memory 256 \
    --monitoring=SYSTEM


gcloud container clusters create ${CLUSTER} \
--location ${REGION} \
--release-channel rapid \
--cluster-version "1.35.2-gke.1842001" \
--enable-image-streaming \
--enable-autoscaling \
--enable-autoprovisioning --max-cpu 1000000 --max-memory 1000000 \
--num-nodes 1


# Activate/create your staging-iam configuration
gcloud config configurations activate staging-iam

# Ensure the overrides are set
gcloud config set api_endpoint_overrides/iam "https://staging-iam.mtls.sandbox.googleapis.com/"
gcloud config set api_endpoint_overrides/cloudresourcemanager "https://cloud-staging-cloudresourcemanager.mtls.sandbox.googleapis.com/"

# Re-apply the crucial permission in IAM Staging
gcloud projects add-iam-policy-binding gke-ai-open-models \
    --member="serviceAccount:<REDACTED_PII>" \
    --role="roles/monitoring.viewer"

# Switch back to your default gcloud config
gcloud config configurations activate default
