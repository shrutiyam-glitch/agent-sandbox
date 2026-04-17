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

from kubernetes.client import ApiException
from k8s_agent_sandbox.constants import (
    PODSNAPSHOT_API_GROUP,
    PODSNAPSHOT_API_KIND,
    PODSNAPSHOT_API_VERSION,
)
from k8s_agent_sandbox.sandbox_client import SandboxClient
from .sandbox_with_snapshot_support import SandboxWithSnapshotSupport

class PodSnapshotSandboxClient(SandboxClient[SandboxWithSnapshotSupport]):
    """
    A specialized Sandbox client for managing Sandboxes with Pod Snapshot feature.
    This class enables users to take snapshot of the Sandbox via GKE Pod Snapshot feature:
    https://docs.cloud.google.com/kubernetes-engine/docs/concepts/pod-snapshots
    """

    sandbox_class = SandboxWithSnapshotSupport

    def __init__(
        self,
        *args, **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.snapshot_crd_installed = self._check_snapshot_crd_installed()
        if not self.snapshot_crd_installed:
            raise RuntimeError(
                "Pod Snapshot Controller is not ready. "
                "Ensure the PodSnapshot CRD is installed."
            )

    def create_sandbox(self, template: str, namespace: str = "default", sandbox_ready_timeout: int = 180, labels: dict[str, str] | None = None, snapshot_id: str | None = None, *, shutdown_after_seconds: int | None = None) -> SandboxWithSnapshotSupport:
        """Provisions new Sandbox claim with optional snapshot_id."""
        annotations = {}
        if snapshot_id:
            annotations["podsnapshot.gke.io/ps-name"] = snapshot_id
            
        return super().create_sandbox(
            template=template,
            namespace=namespace,
            sandbox_ready_timeout=sandbox_ready_timeout,
            labels=labels,
            annotations=annotations,
            shutdown_after_seconds=shutdown_after_seconds
        )

    def _check_snapshot_crd_installed(self) -> bool:
        if getattr(self, "snapshot_crd_installed", False):
            return True
        try:
            resource_list = self.k8s_helper.custom_objects_api.get_api_resources(
                group=PODSNAPSHOT_API_GROUP,
                version=PODSNAPSHOT_API_VERSION,
            )
            if not resource_list or not resource_list.resources:
                return False
            for resource in resource_list.resources:
                if resource.kind == PODSNAPSHOT_API_KIND:
                    return True
            return False
        except ApiException as e:
            if e.status in [403, 404]:
                return False
            raise
