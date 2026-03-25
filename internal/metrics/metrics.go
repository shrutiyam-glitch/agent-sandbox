// Copyright 2026 The Kubernetes Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// nolint:revive
package metrics

import (
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"sigs.k8s.io/controller-runtime/pkg/metrics"
)

type claimLabels struct {
	namespace    string
	templateName string
	launchType   string
	warmPoolName string
	podCondition string
}

var (
	claimTrackerMutex sync.Mutex
	claimTracker      = make(map[claimLabels][]time.Time)
)

const (
	LaunchTypeWarm    = "warm"    // Pod from a SandboxWarmPool
	LaunchTypeCold    = "cold"    // Pod not from a SandboxWarmPool
	LaunchTypeUnknown = "unknown" // Used when Sandbox is nil during failure
)

var (
	// ClaimStartupLatency measures the time from SandboxClaim creation to SandboxClaim Ready state.
	// Labels:
	// - launch_type: "warm", "cold", "unknown"
	// - sandbox_template: the SandboxTemplateRef
	ClaimStartupLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name: "agent_sandbox_claim_startup_latency_ms",
			Help: "End-to-end latency from SandboxClaim creation to Pod Ready state in milliseconds.",
			// Buckets for latency from 50ms to 4 minutes
			Buckets: []float64{50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000, 120000, 240000},
		},
		[]string{"launch_type", "sandbox_template"},
	)

	// SandboxCreationLatency measures the time from Sandbox creation to Pod Ready state.
	// Labels:
	// - namespace: the namespace of the sandbox
	// - launch_type: "warm", "cold", "unknown"
	// - sandbox_template: the SandboxTemplateRef
	SandboxCreationLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name: "agent_sandbox_creation_latency_ms",
			Help: "Latency from Sandbox creation to Pod Ready state in milliseconds. For warm launches, this measures controller synchronization overhead since the Pod is pre-provisioned.",
			// Buckets for latency from 50ms to 10 minutes
			Buckets: []float64{50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000, 120000, 240000, 300000, 600000},
		},
		[]string{"namespace", "launch_type", "sandbox_template"},
	)

	// SandboxClaimCreationTotal calculates the total number of SandboxClaims created.
	// Labels:
	// - namespace: the namespace of the claim
	// - sandbox_template: the SandboxTemplateRef
	// - launch_type: "warm", "cold", "unknown"
	// - warmpool_name: the name of the warm pool (if applicable)
	// - pod_condition: "ready", "not_ready"
	SandboxClaimCreationTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "agent_sandbox_claim_creation_total",
			Help: "Total number of SandboxClaims created, labeled by namespace, sandbox template, launch type, warmpool name, and pod condition.",
		},
		[]string{"namespace", "sandbox_template", "launch_type", "warmpool_name", "pod_condition"},
	)

	// ClaimsPerMinute measures the rate of SandboxClaims created per minute.
	// Labels:
	// - namespace: the namespace of the claim
	// - sandbox_template: the SandboxTemplateRef
	// - launch_type: "warm", "cold", "unknown"
	// - warmpool_name: the name of the warm pool (if applicable)
	// - pod_condition: "ready", "not_ready"
	ClaimsPerMinute = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "agent_sandbox_claims_per_minute",
			Help: "Rate of SandboxClaims created per minute.",
		},
		[]string{"namespace", "sandbox_template", "launch_type", "warmpool_name", "pod_condition"},
	)
)

// Init registers custom metrics with the global controller-runtime registry.
func init() {
	metrics.Registry.MustRegister(ClaimStartupLatency)
	metrics.Registry.MustRegister(SandboxCreationLatency)
	metrics.Registry.MustRegister(SandboxClaimCreationTotal)
	metrics.Registry.MustRegister(ClaimsPerMinute)

	go startRateComputationWorker()
}

func startRateComputationWorker() {
	ticker := time.NewTicker(5 * time.Second)
	for range ticker.C {
		computeClaimsPerMinute()
	}
}

func computeClaimsPerMinute() {
	claimTrackerMutex.Lock()
	defer claimTrackerMutex.Unlock()

	cutoff := time.Now().Add(-time.Minute)

	for labels, timestamps := range claimTracker {
		// Filter timestamps older than 1 minute
		var recent []time.Time
		for _, t := range timestamps {
			if t.After(cutoff) {
				recent = append(recent, t)
			}
		}

		if len(recent) > 0 {
			claimTracker[labels] = recent
		} else {
			delete(claimTracker, labels)
		}

		// Update the gauge
		ClaimsPerMinute.WithLabelValues(
			labels.namespace,
			labels.templateName,
			labels.launchType,
			labels.warmPoolName,
			labels.podCondition,
		).Set(float64(len(recent)))
	}
}

// RecordClaimStartupLatency records the duration since the provided start time.
func RecordClaimStartupLatency(startTime time.Time, launchType, templateName string) {
	duration := float64(time.Since(startTime).Milliseconds())
	ClaimStartupLatency.WithLabelValues(launchType, templateName).Observe(duration)
}

// RecordSandboxCreationLatency records the measured latency duration for a sandbox creation.
func RecordSandboxCreationLatency(duration time.Duration, namespace, launchType, templateName string) {
	SandboxCreationLatency.WithLabelValues(namespace, launchType, templateName).Observe(float64(duration.Milliseconds()))
}

// RecordSandboxClaimCreation increments the total count of created sandbox claims.
func RecordSandboxClaimCreation(namespace, templateName, launchType, warmPoolName, podCondition string) {
	SandboxClaimCreationTotal.WithLabelValues(namespace, templateName, launchType, warmPoolName, podCondition).Inc()

	claimTrackerMutex.Lock()
	defer claimTrackerMutex.Unlock()
	labels := claimLabels{
		namespace:    namespace,
		templateName: templateName,
		launchType:   launchType,
		warmPoolName: warmPoolName,
		podCondition: podCondition,
	}
	claimTracker[labels] = append(claimTracker[labels], time.Now())
}
