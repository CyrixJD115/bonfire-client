<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { daemonHealth, scanResult, activityLog, type ActivityEvent } from '../../stores';
  import DaemonStatusCard from './DaemonStatusCard.svelte';
  import ScanSummaryCard from './ScanSummaryCard.svelte';
  import ActivityLog from './ActivityLog.svelte';

  let healthInterval: ReturnType<typeof setInterval>;

  async function fetchHealth() {
    try {
      const health = await window.bonfire.daemon.health();
      daemonHealth.set(health as any);
    } catch {
      daemonHealth.set(null);
    }
  }

  async function fetchScanStatus() {
    try {
      const status = await window.bonfire.daemon.status();
      scanResult.set(status as any);
    } catch {
      // daemon may not be ready
    }
  }

  onMount(() => {
    fetchHealth();
    fetchScanStatus();
    healthInterval = setInterval(fetchHealth, 10000);
  });

  onDestroy(() => {
    clearInterval(healthInterval);
  });
</script>

<div class="space-y-6">
  <h1 class="text-2xl font-bold text-white uppercase tracking-wider"
    style="text-shadow: 0 0 30px rgba(251,146,60,0.2);">
    Dashboard
  </h1>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <DaemonStatusCard />
    <ScanSummaryCard />
  </div>

  <ActivityLog />
</div>
