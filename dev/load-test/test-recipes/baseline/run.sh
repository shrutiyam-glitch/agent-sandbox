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
