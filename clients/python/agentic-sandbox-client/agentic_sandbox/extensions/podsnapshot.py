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

import logging
import sys
from kubernetes import client, watch
from kubernetes.client import ApiException
from ..sandbox_client import SandboxClient, ExecutionResult
from ..constants import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


class PodSnapshotSandboxClient(SandboxClient):
    """
    A specialized Sandbox client for interacting with the snapshot controller.
    Handles the case only when triggerConfig is type manual.
    """

    def __init__(
        self,
        template_name: str,
        labels: dict[str, str] | None = None,
        namespace: str = "default",
        podsnapshot_timeout: int = 180,
        server_port: int = 8080,
        **kwargs,
    ):
        super().__init__(
            template_name, namespace, labels=labels, server_port=server_port, **kwargs
        )
        self.controller_ready = False
        self.podsnapshot_timeout = podsnapshot_timeout
        self.controller_ready = self.snapshot_controller_ready()

    def snapshot_controller_ready(self) -> bool:
        """
        Checks if the snapshot controller and agent pods are running.
        Checks only self-installed (gps-system) pod snapshot system.
        """

        if self.controller_ready:
            return True
        
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

    def _wait_for_snapshot_processed(self, snapshot_name: str):
        """
        Waits for the PodSnapshotManualTrigger to be processed and a snapshot created.
        """
        w = watch.Watch()
        logging.info(f"Waiting for snapshot '{snapshot_name}' to be processed...")
        
        try:
            for event in w.stream(
                func=self.custom_objects_api.list_namespaced_custom_object,
                namespace=self.namespace,
                group=PODSNAPSHOT_API_GROUP,
                version=PODSNAPSHOT_API_VERSION,
                plural=PODSNAPSHOT_PLURAL,
                field_selector=f"metadata.name={snapshot_name}",
                timeout_seconds=self.podsnapshot_timeout
            ):
                if event["type"] in ["ADDED", "MODIFIED"]:
                    obj = event["object"]
                    status = obj.get("status", {})
                    conditions = status.get("conditions", [])
                    
                    for condition in conditions:
                        if (
                            condition.get("type") == "Triggered"
                            and condition.get("status") == "True"
                            and condition.get("reason") == "Complete"
                        ):
                            logging.info(f"Snapshot '{snapshot_name}' processed successfully.")
                            w.stop()
                            return
        except Exception as e:
            logging.error(f"Error watching snapshot: {e}")
            raise
            
        raise TimeoutError(f"Snapshot '{snapshot_name}' was not processed within {self.podsnapshot_timeout} seconds.")

    # TODO: Method same as wait_for_sandbox_ready in sandbox_client.py, with minor changes. Consider refactoring to avoid code duplication? 
    def _wait_for_restore_ready(self, claim_name: str):
        """
        Waits for the Sandbox (associated with the claim) to be Ready.
        """
        w = watch.Watch()
        logging.info(f"Waiting for restored sandbox '{claim_name}' to be ready...")
        
        try:
            for event in w.stream(
                func=self.custom_objects_api.list_namespaced_custom_object,
                namespace=self.namespace,
                group=SANDBOX_API_GROUP,
                version=SANDBOX_API_VERSION,
                plural=SANDBOX_PLURAL_NAME,
                field_selector=f"metadata.name={claim_name}",
                timeout_seconds=self.podsnapshot_timeout
            ):
                if event["type"] in ["ADDED", "MODIFIED"]:
                    obj = event["object"]
                    status = obj.get("status", {})
                    conditions = status.get("conditions", [])
                    
                    for condition in conditions:
                        if condition.get("type") == "Ready" and condition.get("status") == "True":
                            logging.info(f"Restored sandbox '{claim_name}' is ready.")
                            w.stop()
                            return
        except Exception as e:
            logging.error(f"Error watching restored sandbox: {e}")
            raise

        raise TimeoutError(f"Restored sandbox '{claim_name}' did not become ready within {self.podsnapshot_timeout} seconds.")

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
            self._wait_for_snapshot_processed(snapshot_name)
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
        except TimeoutError as e:
             return ExecutionResult(
                stdout="",
                stderr=f"Snapshot creation timed out: {e}",
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
        
        claim_name = f"{name}-from-snapshot"
        manifest = {
            "apiVersion": f"{CLAIM_API_GROUP}/{CLAIM_API_VERSION}",
            "kind": "SandboxClaim",
            "metadata": {
                "name": claim_name,
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
            self._wait_for_restore_ready(claim_name)
            return ExecutionResult(
                stdout=f"SandboxClaim '{claim_name}' created successfully.",
                stderr="",
                exit_code=0
            )
        except ApiException as e:
            return ExecutionResult(
                stdout="",
                stderr=f"Failed to create SandboxClaim: {e}",
                exit_code=1
            )
        except TimeoutError as e:
            return ExecutionResult(
                stdout="",
                stderr=f"Restore operation timed out: {e}",
                exit_code=1
            )
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: Add additional cleanup logic here (e.g., delete snapshots, delete sanndboxclaims created from snapshots)
        super().__exit__(exc_type, exc_val, exc_tb)


# add wait for snapshot to be ready logic - done
# add wait for restore to be ready logic - done
# test workload trigger type 
# right now this only works for manual trigger type, add support for workload trigger type
# use a better python sandbox runtime example to follow
# add clean up logic in exit


# add unit tests for pod snapshot client
# add e2e tests for pod snapshot client
# add docs for pod snapshot client
# add error handling for snapshot and restore methods
# add logging for snapshot and restore methods
# split the code into smaller prs for easier review
