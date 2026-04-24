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
