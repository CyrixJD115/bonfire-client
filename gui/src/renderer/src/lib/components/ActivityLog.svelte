<script lang="ts">
  import { activityLog } from '../../stores';

  $: events = $activityLog;
</script>

<div class="bg-deep-800/80 border border-deep-600/50 p-5 shadow-block shadow-black/40 backdrop-blur-sm rounded-none">
  <h3 class="text-base font-bold text-white uppercase tracking-wider border-b border-deep-600/30 pb-2 mb-4"
    style="text-shadow: 0 0 20px rgba(251,146,60,0.15);">
    Activity
  </h3>
  {#if events.length}
    <div class="space-y-1 max-h-64 overflow-y-auto">
      {#each events as event}
        <div class="flex items-start gap-2 py-1.5 border-b border-deep-700/30 last:border-0">
          <span
            class="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
            class:bg-emerald-400!={event.type === 'success'}
            class:bg-ember-400!={event.type === 'warning'}
            class:bg-flame-400!={event.type === 'error'}
            class:bg-deep-100!={event.type === 'info'} />
          <div class="flex-1 min-w-0">
            <div class="text-xs text-deep-200 font-mono">{event.message}</div>
            <div class="text-[10px] text-deep-300 font-mono mt-0.5">{event.timestamp}</div>
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="text-sm text-deep-300">No recent activity.</div>
  {/if}
</div>
