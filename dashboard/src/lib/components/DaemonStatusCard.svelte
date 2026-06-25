<script lang="ts">
  import { daemonHealth } from '../../stores';

  $: health = $daemonHealth;
  $: isRunning = health?.status === 'running';
</script>

<div class="card">
  <h3 class="card-header">Daemon Status</h3>
  {#if health}
    <div class="space-y-2 text-sm">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full inline-block"
          class:bg-emerald-400={isRunning} class:shadow-[0_0_8px_rgba(52,211,153,0.6)]={isRunning}
          class:bg-gray-500={!isRunning}></span>
        <span class="text-deep-50 font-medium uppercase tracking-wider">{health.status}</span>
      </div>
      <div class="text-deep-200 font-mono text-xs">
        <span class="text-deep-100">Uptime:</span> {health.uptime}
      </div>
      <div class="text-deep-200 font-mono text-xs">
        <span class="text-deep-100">Version:</span> {health.version}
      </div>
    </div>
  {:else}
    <div class="flex items-center gap-2 text-sm text-deep-300">
      <span class="w-2 h-2 rounded-full bg-gray-500"></span>
      <span>Connecting...</span>
    </div>
  {/if}
</div>
