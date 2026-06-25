<script lang="ts">
  import { scanResult } from '../../stores';

  $: scan = $scanResult;
</script>

<div class="card">
  <h3 class="card-header">Last Scan</h3>
  {#if scan}
    <div class="space-y-2 text-sm">
      <div class="flex justify-between">
        <span class="text-deep-200">Games Found</span>
        <span class="text-ember-400 font-mono font-bold">{scan.games_found}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-deep-200">Save Files</span>
        <span class="text-ember-400 font-mono font-bold">{scan.save_files}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-deep-200">Last Scan</span>
        <span class="text-deep-50 font-mono text-xs">{scan.last_scan}</span>
      </div>
      {#if scan.errors?.length}
        <div class="mt-2 pt-2 border-t border-flame-700/50">
          <span class="text-flame-400 text-xs uppercase tracking-wider font-semibold">Errors</span>
          {#each scan.errors as err}
            <div class="text-flame-300 font-mono text-xs mt-1">{err}</div>
          {/each}
        </div>
      {/if}
    </div>
  {:else}
    <div class="text-sm text-deep-300">No scan data yet.</div>
  {/if}
</div>
