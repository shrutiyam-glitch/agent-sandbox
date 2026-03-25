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
        --release-channel=rapid # important for AutoScalingMetric


gcloud beta container node-pools create "${NODE_POOL}" \
        --project="${PROJECT_ID}" \
        --cluster="${CLUSTER}" \
        --region="${REGION}" \
        --node-locations="${NODE_LOCATIONS}" \
        --num-nodes=1 \
        --image-type=cos_containerd \
        --machine-type="${MACHINE_TYPE}" \
        --sandbox=type=gvisor

#
# HELP agent_sandbox_warmpool_replicas Current number of replicas in the SandboxWarmPool.
# TYPE agent_sandbox_warmpool_replicas gauge
# agent_sandbox_warmpool_replicas{name="python-sdk-warmpool",namespace="default",template_name="python-counter-template"} 2
# agent_sandbox_warmpool_replicas{name="python-sdk-warmpool",namespace="sandbox-test",template_name="python-counter-template"} 2
