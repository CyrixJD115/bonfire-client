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
      class="px-5 py-2.5 font-semibold text-sm uppercase tracking-wider text-white
        bg-ember-600 hover:bg-ember-500 disabled:opacity-50 disabled:cursor-not-allowed
        border border-ember-400/30 shadow-block shadow-black/40
        active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_0px_rgba(0,0,0,0.6)]
        transition-all"
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
