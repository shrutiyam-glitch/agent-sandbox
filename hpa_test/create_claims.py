import threading
from kubernetes import client, config
import yaml
import time

# Configuration
NAMESPACE = "sandbox-test"
TEMPLATE = "python-sandbox-template"
COUNT = 30

# barrier = threading.Barrier(COUNT)

def create_sandbox_claim(name):
    # Load in-cluster or local kubeconfig

    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    custom_objects_api = client.CustomObjectsApi()
    
    claim = {
        "apiVersion": "extensions.agents.x-k8s.io/v1alpha1",
        "kind": "SandboxClaim",
        "metadata": {
            "name": name,
            "namespace": NAMESPACE,
            "labels": {
                "app": "agent-sandbox-workload"
            }
        },
        "spec": {
            "sandboxTemplateRef": {
                "name": TEMPLATE
            }
        }
    }

    # barrier.wait()

    try:
        custom_objects_api.create_namespaced_custom_object(
            group="extensions.agents.x-k8s.io",
            version="v1alpha1",
            namespace=NAMESPACE,
            plural="sandboxclaims",
            body=claim
        )
        print(f"Successfully created {name}")
    except Exception as e:
        print(f"Failed to create {name}: {e}")

if __name__ == "__main__":
    threads = []
    for i in range(1, COUNT + 1):
        name = f"sandboxclaim-{i}"
        create_sandbox_claim(name)
        # time.sleep(1)
        t = threading.Thread(target=create_sandbox_claim, args=(name,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
# run every second - steady creation of sandboxclaim - for tenminutes 
