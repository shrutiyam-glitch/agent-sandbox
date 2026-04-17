import time
import subprocess

# Config: Adjust based on your pod resources (e.g., 500m = 0.5)
VCPU_PER_POD = 1.0 
NAMESPACE = "sandbox-test"
LOG_FILE = "resource_usage_static.csv"

print("Logging vCPU usage... Press Ctrl+C to stop.")
with open(LOG_FILE, 'w') as f:
    f.write("timestamp,pod_count\n")
    try:
        while True:
            # Get current ready replicas in the warmpool
            cmd = f"kubectl get sandboxwarmpool python-sdk-warmpool -n {NAMESPACE} -o jsonpath='{{.status.readyReplicas}}'"
            pods = subprocess.check_output(cmd, shell=True).decode('utf-8')
            count = int(pods) if pods else 0
            
            f.write(f"{time.time()},{count}\n")
            f.flush()
            time.sleep(2)
    except KeyboardInterrupt:
        print("Logging stopped.")