<script lang="ts">
  import { daemonHealth } from '../../stores';

  $: health = $daemonHealth;
  $: isRunning = health?.status === 'running';
</script>

<div class="bg-deep-800/80 border border-deep-600/50 p-5 shadow-block shadow-black/40 backdrop-blur-sm rounded-none">
  <h3 class="text-base font-bold text-white uppercase tracking-wider border-b border-deep-600/30 pb-2 mb-4"
    style="text-shadow: 0 0 20px rgba(251,146,60,0.15);">
    Daemon Status
  </h3>
  {#if health}
    <div class="space-y-2 text-sm">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full inline-block"
          class:bg-emerald-400 class:shadow-[0_0_8px_rgba(52,211,153,0.6)]={isRunning}
          class:bg-gray-500={!isRunning} />
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
      <span class="w-2 h-2 rounded-full bg-gray-500" />
      <span>Connecting...</span>
    </div>
  {/if}
</div>
