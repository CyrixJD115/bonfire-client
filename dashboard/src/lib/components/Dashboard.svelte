<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { daemonHealth, scanResult, activityLog, type ActivityEvent } from '../../stores';
  import { fetchHealth, fetchStatus, triggerScan } from '../../api';
  import DaemonStatusCard from './DaemonStatusCard.svelte';
  import ScanSummaryCard from './ScanSummaryCard.svelte';
  import ActivityLog from './ActivityLog.svelte';

  let healthInterval: ReturnType<typeof setInterval>;
  let scanning = false;

  async function pollHealth() {
    try {
      const health = await fetchHealth();
      daemonHealth.set(health);
    } catch {
      daemonHealth.set(null);
    }
  }

  async function pollStatus() {
    try {
      const status = await fetchStatus();
      scanResult.set(status);
    } catch {
      // daemon may not be ready
    }
  }

  async function handleScan() {
    scanning = true;
    try {
      const result = await triggerScan();
      scanResult.set(result);
      activityLog.update(log => [...log, {
        timestamp: new Date().toLocaleString(),
        message: 'Scan complete',
        type: 'success',
      }]);
    } catch (err) {
      activityLog.update(log => [...log, {
        timestamp: new Date().toLocaleString(),
        message: `Scan failed: ${err}`,
        type: 'error',
      }]);
    } finally {
      scanning = false;
    }
  }

  onMount(() => {
    pollHealth();
    pollStatus();
    healthInterval = setInterval(pollHealth, 10000);
  });

  onDestroy(() => {
    clearInterval(healthInterval);
  });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold text-white uppercase tracking-wider"
      style="text-shadow: 0 0 30px rgba(251,146,60,0.2);">
      Dashboard
    </h1>
    <button
      onclick={handleScan}
      disabled={scanning}
      class="btn btn-primary"
    >
      {scanning ? 'Scanning...' : 'Run Scan'}
    </button>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <DaemonStatusCard />
    <ScanSummaryCard />
  </div>

  <ActivityLog />
</div>
