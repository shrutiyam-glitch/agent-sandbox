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
from kubernetes import client, config, watch
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
        snapshot_id: str | None = None,
        **kwargs,
    ):
        
        self.controller_ready = False
        self.podsnapshot_timeout = podsnapshot_timeout
        self.created_snapshots = []
        self.namespace = namespace
        self.annotations = None
        self.controller_ready = self.snapshot_controller_ready()

        if snapshot_id:
            self._configure_snapshot_restore(snapshot_id)

        super().__init__(
            template_name, namespace, labels=labels, annotations=self.annotations, server_port=server_port, **kwargs
        )

    def _configure_snapshot_restore(self, snapshot_id: str):
        """
        Resolves the snapshot ID to a UID, checks readiness, and sets up labels for restoration.
        """
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        self.custom_objects_api = client.CustomObjectsApi()
        try:
            logging.info(f"Resolving snapshot ID for trigger '{snapshot_id}'...")
            uid = self._get_snapshot_uid(snapshot_id)
            self._check_snapshot_ready(uid)
            if self.annotations is None:
                self.annotations = {}
            self.annotations["podsnapshot.gke.io/ps-name"] = uid
            logging.info(f"Using snapshot UID '{uid}' for sandbox restoration.")
        except Exception as e:
            logging.error(f"Failed to prepare snapshot '{snapshot_id}': {e}")
            raise


    def _check_snapshot_ready(self, snapshot_uid: str):
        """
        Checks if the PodSnapshot resource is in Ready state.
        """
        logging.info(f"Checking if PodSnapshot '{snapshot_uid}' is ready...")
        try:
            snapshot = self.custom_objects_api.get_namespaced_custom_object(
                group=PODSNAPSHOT_API_GROUP,
                version=PODSNAPSHOT_API_VERSION,
                namespace=self.namespace,
                plural=PODSNAPSHOT_PLURAL,
                name=snapshot_uid
            )
            
            status = snapshot.get("status", {})
            conditions = status.get("conditions", [])
            
            is_ready = False
            for condition in conditions:
                if condition.get("type") == "Ready" and condition.get("status") == "True":
                    is_ready = True
                    break
            
            if not is_ready:
                raise RuntimeError(f"PodSnapshot '{snapshot_uid}' is not in Ready state.")
                
            logging.info(f"PodSnapshot '{snapshot_uid}' is ready.")

        except ApiException as e:
            logging.error(f"Failed to get PodSnapshot '{snapshot_uid}': {e}")
            raise

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
                plural=PODSNAPSHOTMANUALTRIGGER_PLURAL,
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

    def _get_snapshot_uid(self, snapshot_name: str) -> str:
        """
        Retrieves the UID of the specified PodSnapshot resource.
        """
        try:
            snapshot = self.custom_objects_api.get_namespaced_custom_object(
                group=PODSNAPSHOT_API_GROUP,
                version=PODSNAPSHOT_API_VERSION,
                namespace=self.namespace,
                plural=PODSNAPSHOTMANUALTRIGGER_PLURAL,
                name=snapshot_name
            )
            return snapshot["status"]["snapshotCreated"]["name"]
        except ApiException as e:
            logging.error(f"Failed to retrieve PodSnapshot '{snapshot_name}': {e}")
            raise

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
                plural=PODSNAPSHOTMANUALTRIGGER_PLURAL,
                body=manifest
            )
            self._wait_for_snapshot_processed(snapshot_name)
            self.created_snapshots.append(snapshot_name)
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
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleans up created snapshots and triggers."""
        for trigger_name in self.created_snapshots:
            try:
                # Retrieve the snapshot name from the trigger status
                snapshot_name = self._get_snapshot_uid(trigger_name)
                
                # Delete the PodSnapshot
                if snapshot_name:
                    logging.info(f"Deleting PodSnapshot: {snapshot_name}")
                    try:
                        self.custom_objects_api.delete_namespaced_custom_object(
                            group=PODSNAPSHOT_API_GROUP,
                            version=PODSNAPSHOT_API_VERSION,
                            namespace=self.namespace,
                            plural=PODSNAPSHOT_PLURAL,
                            name=snapshot_name
                        )
                    except ApiException as e:
                        if e.status != 404:
                            logging.error(f"Failed to delete PodSnapshot '{snapshot_name}': {e}")
            except Exception as e:
                # If retrieving the snapshot UID fails, we still proceed to delete the trigger
                logging.error(f"Error retrieving snapshot name for trigger '{trigger_name}': {e}")

            # Delete the PodSnapshotManualTrigger
            try:
                logging.info(f"Deleting PodSnapshotManualTrigger: {trigger_name}")
                self.custom_objects_api.delete_namespaced_custom_object(
                    group=PODSNAPSHOT_API_GROUP,
                    version=PODSNAPSHOT_API_VERSION,
                    namespace=self.namespace,
                    plural=PODSNAPSHOTMANUALTRIGGER_PLURAL,
                    name=trigger_name
                )
            except ApiException as e:
                if e.status != 404:
                    logging.error(f"Failed to delete PodSnapshotManualTrigger '{trigger_name}': {e}")

        logging.info("Cleanup of snapshots and triggers completed.")
        super().__exit__(exc_type, exc_val, exc_tb)

