# Example: Granting monitoring.viewer to custom-metrics-adapter-sa
SERVICE_ACCOUNT_EMAIL="custom-metrics-adapter-sa@gke-ai-open-models.iam.gserviceaccount.com"
ROLE_TO_GRANT="roles/monitoring.viewer"

gcloud projects add-iam-policy-binding gke-ai-open-models \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="${ROLE_TO_GRANT}"
