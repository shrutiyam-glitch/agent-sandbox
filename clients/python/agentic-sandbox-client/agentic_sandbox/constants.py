# Constants for API Groups and Resources
GATEWAY_API_GROUP = "gateway.networking.k8s.io"
GATEWAY_API_VERSION = "v1"
GATEWAY_PLURAL = "gateways"

CLAIM_API_GROUP = "extensions.agents.x-k8s.io"
CLAIM_API_VERSION = "v1alpha1"
CLAIM_PLURAL_NAME = "sandboxclaims"

SANDBOX_API_GROUP = "agents.x-k8s.io"
SANDBOX_API_VERSION = "v1alpha1"
SANDBOX_PLURAL_NAME = "sandboxes"

POD_NAME_ANNOTATION = "agents.x-k8s.io/pod-name"

PODSNAPSHOT_API_GROUP = "podsnapshot.gke.io"
PODSNAPSHOT_API_VERSION = "v1alpha1"
PODSNAPSHOT_PLURAL = "podsnapshotmanualtriggers"

SNAPSHOT_NAMESPACE = "gps-system"
SNAPSHOT_CONTROLLER_NAME = "gke-pod-snapshot-controller"
