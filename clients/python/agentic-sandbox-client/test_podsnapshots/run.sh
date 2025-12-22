source ./env.sh

gcloud container clusters create "${CLUSTER}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --cluster-version=${CLUSTER_VERSION} \
        --num-nodes=1 \
        --node-locations="${NODE_LOCATIONS}" \
        --workload-pool="${PROJECT_ID}.svc.id.goog" \
        --workload-metadata=GKE_METADATA \
        --gateway-api=standard

gcloud container node-pools create "e2-nodepool" \
        --project="${PROJECT_ID}" \
        --cluster="${CLUSTER}" \
        --region="${REGION}" \
        --node-locations="${NODE_LOCATIONS}" \
        --num-nodes=1 \
        --image-type=cos_containerd \
        --machine-type=e2-standard-2 \
        --sandbox=type=gvisor

envsubst < gps-all.yaml | kubectl apply -f -

# create namespace and PodSnapshot resources
# create the serviceaccount

kubectl apply \
-f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/${AGENT_SANDBOX_VERSION}/manifest.yaml \
-f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/${AGENT_SANDBOX_VERSION}/extensions.yaml


envsubst < python-sandbox-template.yaml | kubectl apply -f -

envsubst < sandbox_router.yaml | kubectl apply -f -

kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml 

kubectl apply -f ./gateway.yaml

cd ..

python3 test_podsnapshot_extension.py --template-name python-runtime-template --namespace sandbox-test --labels app=agent-sandbox-workload --gateway-name external-http-gateway --gateway-namespace sandbox-test
