<script lang="ts">
  import { onMount } from 'svelte';
  import { games, serverHealth, daemonConfig, type GameEntry } from '../../stores';
  import { fetchGames, fetchServerHealth, fetchConfig } from '../../api';

  let searchQuery = '';
  let storefrontFilter: 'all' | 'Steam' | 'Heroic' = 'all';
  let statusFilter: 'all' | 'local_only' | 'synced' | 'outdated' | 'unwatched' = 'all';
  let loading = true;
  let error = '';

  $: filteredGames = $games.filter(g => {
    if (storefrontFilter !== 'all' && g.storefront !== storefrontFilter) return false;
    if (statusFilter !== 'all' && g.sync_status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!g.title.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  $: gameCounts = {
    total: $games.length,
    steam: $games.filter(g => g.storefront === 'Steam').length,
    heroic: $games.filter(g => g.storefront === 'Heroic').length,
    withSaves: $games.filter(g => g.has_save_files).length,
  };

  onMount(async () => {
    try {
      const [gameData, healthResult, configResult] = await Promise.all([
        fetchGames(),
        fetchServerHealth(),
        fetchConfig(),
      ]);
      games.set(gameData.games);
      serverHealth.set(healthResult);
      daemonConfig.set(configResult);
    } catch (e) {
      error = String(e);
    } finally {
      loading = false;
    }
  });

  function syncBadgeClass(status: string): string {
    switch (status) {
      case 'synced': return 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30';
      case 'local_only': return 'bg-flame-600/20 text-flame-400 border-flame-600/30';
      case 'outdated': return 'bg-red-600/20 text-red-400 border-red-600/30';
      case 'unwatched': return 'bg-deep-700/40 text-deep-300 border-deep-600/30';
      default: return 'bg-deep-700/40 text-deep-300 border-deep-600/30';
    }
  }

  function syncLabel(status: string): string {
    switch (status) {
      case 'synced': return 'Synced';
      case 'local_only': return 'Local';
      case 'outdated': return 'Outdated';
      case 'unwatched': return 'Unwatched';
      default: return status;
    }
  }

  function goToServer() {
    const cfg = $daemonConfig;
    if (cfg) {
      window.open(cfg.server_web_url, '_blank');
    }
  }
</script>

<div class="w-full space-y-6">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold text-white uppercase tracking-wider"
      style="text-shadow: 0 0 30px rgba(251,146,60,0.2);">
      Games
    </h1>
    <div class="flex items-center gap-3">
      {#if $serverHealth}
        <a
          href={$daemonConfig?.server_web_url ?? '#'}
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-2 text-xs uppercase tracking-wider font-medium px-3 py-1.5 rounded
            {$serverHealth.connected
              ? 'bg-emerald-600/10 text-emerald-400 border border-emerald-600/30 hover:bg-emerald-600/20'
              : 'bg-deep-800/40 text-deep-400 border border-deep-700/30'}"
        >
          <span class="w-1.5 h-1.5 rounded-full"
            class:bg-emerald-400={$serverHealth.connected}
            class:bg-deep-500={!$serverHealth.connected}
          ></span>
          Server {$serverHealth.connected ? 'Online' : 'Offline'}
        </a>
      {/if}
    </div>
  </div>

  <div class="flex items-center gap-3 text-xs uppercase tracking-wider text-deep-300">
    <span>{gameCounts.total} total</span>
    <span class="text-deep-600">|</span>
    <span class="text-sky-400">{gameCounts.steam} Steam</span>
    <span class="text-deep-600">|</span>
    <span class="text-amber-400">{gameCounts.heroic} Heroic</span>
    <span class="text-deep-600">|</span>
    <span class="text-emerald-400">{gameCounts.withSaves} with saves</span>
  </div>

  <div class="flex flex-wrap items-center gap-3">
    <input
      type="text"
      bind:value={searchQuery}
      placeholder="Search games..."
      class="input flex-1 min-w-[200px]"
    />
    <select bind:value={storefrontFilter} class="input w-auto">
      <option value="all">All Stores</option>
      <option value="Steam">Steam</option>
      <option value="Heroic">Heroic</option>
    </select>
    <select bind:value={statusFilter} class="input w-auto">
      <option value="all">All Status</option>
      <option value="synced">Synced</option>
      <option value="local_only">Local Only</option>
      <option value="outdated">Outdated</option>
      <option value="unwatched">Unwatched</option>
    </select>
  </div>

  {#if loading}
    <div class="text-center text-deep-400 py-12">
      <div class="inline-block w-6 h-6 border-2 border-ember-500 border-t-transparent rounded-full animate-spin mb-2"></div>
      <div class="text-xs uppercase tracking-wider">Scanning for games...</div>
    </div>
  {:else if error}
    <div class="card border-red-600/30 bg-red-600/5">
      <p class="text-red-400 text-sm">{error}</p>
      <p class="text-deep-400 text-xs mt-1">Make sure the Bonfire daemon is running on port 21466.</p>
    </div>
  {:else if filteredGames.length === 0}
    <div class="text-center text-deep-400 py-16">
      <div class="text-4xl mb-3 opacity-40">◆</div>
      <p class="text-sm uppercase tracking-wider">
        {$games.length === 0 ? 'No games found. Run a scan from the Dashboard.' : 'No games match your filters.'}
      </p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
      {#each filteredGames as game (game.id)}
        <div class="card flex flex-col">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0 flex-1">
              <h3 class="text-sm font-bold text-white truncate uppercase tracking-wider">{game.title}</h3>
              <div class="flex items-center gap-2 mt-1">
                <span class="text-xs px-1.5 py-0.5 rounded border uppercase tracking-wider font-medium
                  {game.storefront === 'Steam' ? 'bg-sky-600/20 text-sky-400 border-sky-600/30' : 'bg-amber-600/20 text-amber-400 border-amber-600/30'}">
                  {game.storefront}
                </span>
                <span class="text-xs text-deep-400">{game.platform}</span>
              </div>
            </div>
            <span class="text-xs px-2 py-0.5 rounded border uppercase tracking-wider font-medium whitespace-nowrap {syncBadgeClass(game.sync_status)}">
              {syncLabel(game.sync_status)}
            </span>
          </div>

          <div class="flex items-center gap-4 mt-3 text-xs text-deep-400">
            {#if game.save_dir}
              <span class="truncate max-w-[200px]" title={game.save_dir}>
                {game.save_dir}
              </span>
            {:else if game.install_path}
              <span class="truncate max-w-[200px]" title={game.install_path}>
                {game.install_path}
              </span>
            {:else}
              <span class="italic">No install path</span>
            {/if}
          </div>

          <div class="flex items-center gap-3 mt-2 text-xs">
            {#if game.file_count > 0}
              <span class="text-deep-300">{game.file_count} save file{game.file_count !== 1 ? 's' : ''}</span>
            {:else}
              <span class="text-deep-500 italic">No save files</span>
            {/if}
            {#if game.local_hash}
              <span class="text-deep-500 font-mono text-[10px]">{game.local_hash}</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
