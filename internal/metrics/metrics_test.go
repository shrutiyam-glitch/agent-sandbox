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
	"testing"
	"time"

	"github.com/prometheus/client_golang/prometheus/testutil"
)

func TestClaimLatencyRecording(t *testing.T) {
	testCases := []struct {
		name       string
		launchType string
	}{
		{"Warm", LaunchTypeWarm},
		{"Cold", LaunchTypeCold},
		{"Unknown", LaunchTypeUnknown},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			ClaimStartupLatency.Reset()
			ClaimStartupLatency.WithLabelValues(tc.launchType, "test-tmpl").Observe(1000)

			if testutil.CollectAndCount(ClaimStartupLatency) != 1 {
				t.Errorf("Expected 1 observation")
			}
		})
	}
}

func TestClaimsPerMinuteRecording(t *testing.T) {
	// Reset any existing state
	ClaimsPerMinute.Reset()
	claimTrackerMutex.Lock()
	claimTracker = make(map[claimLabels][]time.Time)
	claimTrackerMutex.Unlock()

	labels := claimLabels{
		namespace:    "default",
		templateName: "test-tmpl",
		launchType:   LaunchTypeCold,
		warmPoolName: "none",
		podCondition: "not_ready",
	}

	// Add 3 claims, two within the last minute, one older than a minute
	now := time.Now()
	claimTrackerMutex.Lock()
	claimTracker[labels] = []time.Time{
		now.Add(-2 * time.Minute),
		now.Add(-30 * time.Second),
		now.Add(-10 * time.Second),
	}
	claimTrackerMutex.Unlock()

	// Compute metrics manually (simulating the worker)
	computeClaimsPerMinute()

	// Assert the gauge metric exposes the value 2
	gaugeValue := testutil.ToFloat64(ClaimsPerMinute.WithLabelValues(
		labels.namespace,
		labels.templateName,
		labels.launchType,
		labels.warmPoolName,
		labels.podCondition,
	))

	if gaugeValue != 2.0 {
		t.Errorf("Expected ClaimsPerMinute gauge to be 2.0, got %f", gaugeValue)
	}

	// Wait 1 minute and 10 seconds effectively, by shifting time, or just manually injecting older time
	// To keep test fast, simply update the tracker with older times
	claimTrackerMutex.Lock()
	claimTracker[labels] = []time.Time{
		now.Add(-90 * time.Second),
		now.Add(-70 * time.Second),
	}
	claimTrackerMutex.Unlock()

	// Compute metrics manually again
	computeClaimsPerMinute()

	// Verify gauge drops to zero when older timestamps are cleared
	gaugeValueZero := testutil.ToFloat64(ClaimsPerMinute.WithLabelValues(
		labels.namespace,
		labels.templateName,
		labels.launchType,
		labels.warmPoolName,
		labels.podCondition,
	))

	if gaugeValueZero != 0.0 {
		t.Errorf("Expected ClaimsPerMinute gauge to drop to 0.0, got %f", gaugeValueZero)
	}
}

func TestSandboxCreationLatencyRecording(t *testing.T) {
	testCases := []struct {
		name       string
		launchType string
	}{
		{"Warm", LaunchTypeWarm},
		{"Cold", LaunchTypeCold},
		{"Unknown", LaunchTypeUnknown},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			SandboxCreationLatency.Reset()
			RecordSandboxCreationLatency(1000*time.Millisecond, "default", tc.launchType, "test-tmpl")

			if testutil.CollectAndCount(SandboxCreationLatency) != 1 {
				t.Errorf("Expected 1 observation")
			}
		})
	}
}

func TestSandboxClaimCreationRecording(t *testing.T) {
	testCases := []struct {
		name         string
		launchType   string
		podCondition string
	}{
		{"WarmReady", LaunchTypeWarm, "ready"},
		{"WarmNotReady", LaunchTypeWarm, "not_ready"},
		{"Cold", LaunchTypeCold, "not_ready"},
		{"Unknown", LaunchTypeUnknown, "not_ready"},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			SandboxClaimCreationTotal.Reset()
			SandboxClaimCreationTotal.WithLabelValues("default", "test-tmpl", tc.launchType, "test-pool", tc.podCondition).Inc()

			if testutil.CollectAndCount(SandboxClaimCreationTotal) != 1 {
				t.Errorf("Expected 1 observation")
			}
		})
	}
}
