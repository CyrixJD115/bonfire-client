<script lang="ts">
  import { activityLog } from '../../stores';

  $: events = $activityLog;
</script>

<div class="card">
  <h3 class="card-header">Activity</h3>
  {#if events.length}
    <div class="space-y-1 max-h-64 overflow-y-auto">
      {#each events as event}
        <div class="flex items-start gap-2 py-1.5 border-b border-deep-700/30 last:border-0">
          <span
            class="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
            class:bg-emerald-400!={event.type === 'success'}
            class:bg-ember-400!={event.type === 'warning'}
            class:bg-flame-400!={event.type === 'error'}
            class:bg-deep-100!={event.type === 'info'}></span>
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
