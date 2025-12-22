# Copyright 2025 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law of agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from kubernetes import client
import time
from kubernetes.client import ApiException
from ..sandbox_client import SandboxClient, ExecutionResult, CLAIM_API_GROUP, CLAIM_API_VERSION, CLAIM_PLURAL_NAME

PODSNAPSHOT_API_GROUP = "podsnapshot.gke.io"
PODSNAPSHOT_API_VERSION = "v1alpha1"
PODSNAPSHOT_PLURAL = "podsnapshotmanualtriggers"

class PodSnapshotSandboxClient(SandboxClient):
    """
    A specialized Sandbox client for interacting with the snapshot controller.
    Handles the case only when triggerConfig is type manual. 
    """
    def __init__(self, template_name: str, labels: dict[str, str] | None = None, namespace: str = "default", server_port: int = 8080, **kwargs):
        super().__init__(template_name, namespace, labels=labels, server_port=server_port, **kwargs)
        self.controller_ready = False

    def snapshot_controller_ready(self) -> bool:
        """
        Checks if the snapshot controller and agent pods are running.
        Checks only self-installed (gps-system) pod snapshot system.
        """
        SNAPSHOT_NAMESPACE = "gps-system"
        SNAPSHOT_CONTROLLER_NAME = "gke-pod-snapshot-controller"

        v1 = client.CoreV1Api()
    
        try:
            pods = v1.list_namespaced_pod(SNAPSHOT_NAMESPACE)
            
            controller_ready = False
            
            for pod in pods.items:
                name = pod.metadata.name
                if pod.status.phase == "Running":
                    if SNAPSHOT_CONTROLLER_NAME in name:
                        controller_ready = True
            
            if controller_ready:
               self.controller_ready = True
                
        except ApiException:
            self.controller_ready = False

        return self.controller_ready

    def checkpoint_sandbox(self, snapshot_name: str) -> ExecutionResult:
        """
        Triggers a snapshot of the specified pod by creating a PodSnapshotManualTrigger resource.
        """
        if not self.controller_ready:
            return ExecutionResult(
                stdout="",
                stderr="Snapshot controller is not ready. Ensure it is installed and running.",
                exit_code=1
            )
        if not self.pod_name:
            return ExecutionResult(
                stdout="",
                stderr="Sandbox pod name not found. Ensure sandbox is created.",
                exit_code=1
            )

        manifest = {
            "apiVersion": f"{PODSNAPSHOT_API_GROUP}/{PODSNAPSHOT_API_VERSION}",
            "kind": "PodSnapshotManualTrigger",
            "metadata": {
                "name": snapshot_name,
                "namespace": self.namespace
            },
            "spec": {
                "targetPod": self.pod_name
            }
        }

        try:
            self.custom_objects_api.create_namespaced_custom_object(
                group=PODSNAPSHOT_API_GROUP,
                version=PODSNAPSHOT_API_VERSION,
                namespace=self.namespace,
                plural=PODSNAPSHOT_PLURAL,
                body=manifest
            )
            time.sleep(60)  # Todo: Wait for snapshot to be processed
            return ExecutionResult(
                stdout=f"PodSnapshotManualTrigger '{snapshot_name}' created successfully.",
                stderr="",
                exit_code=0
            )
        except ApiException as e:
            return ExecutionResult(
                stdout="",
                stderr=f"Failed to create PodSnapshotManualTrigger: {e}",
                exit_code=1
            )

    def restore_sandbox(self, name: str) -> ExecutionResult:
        """
        Restores a sandbox from a snapshot by creating a SandboxClaim resource.
        """
        if not self.controller_ready:
            return ExecutionResult(
                stdout="",
                stderr="Snapshot controller is not ready. Ensure it is installed and running.",
                exit_code=1
            )
        
        manifest = {
            "apiVersion": f"{CLAIM_API_GROUP}/{CLAIM_API_VERSION}",
            "kind": "SandboxClaim",
            "metadata": {
                "name": f"{name}-from-snapshot",
                "namespace": self.namespace,
                "labels": self.labels if self.labels else {}
            },
            "spec": {
                "sandboxTemplateRef": {
                    "name": self.template_name
                }
            }
        }

        try:
            self.custom_objects_api.create_namespaced_custom_object(
                group=CLAIM_API_GROUP,
                version=CLAIM_API_VERSION,
                namespace=self.namespace,
                plural=CLAIM_PLURAL_NAME,
                body=manifest
            )
            time.sleep(60)  # Todo: Wait for snapshot to be processed
            return ExecutionResult(
                stdout=f"SandboxClaim '{name}-from-snapshot' created successfully.",
                stderr="",
                exit_code=0
            )
        except ApiException as e:
            return ExecutionResult(
                stdout="",
                stderr=f"Failed to create SandboxClaim: {e}",
                exit_code=1
            )
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: Add additional cleanup logic here (e.g., delete snapshots, delete sanndboxclaims created from snapshots)
        super().__exit__(exc_type, exc_val, exc_tb)

