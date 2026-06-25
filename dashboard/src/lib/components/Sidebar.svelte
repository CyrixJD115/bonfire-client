<script lang="ts">
  import { onMount } from 'svelte';
  import { currentView, daemonHealth, daemonConfig, serverHealth, type View } from '../../stores';
  import { quitDaemon, fetchConfig, fetchServerHealth } from '../../api';
  import FlameLayer from './FlameLayer.svelte';

  const navItems: { id: View; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '◆' },
    { id: 'games', label: 'Games', icon: '⬡' },
    { id: 'settings', label: 'Settings', icon: '⚙' },
  ];

  $: health = $daemonHealth;
  $: isOnline = health?.status === 'running';

  let configLoaded = false;

  onMount(async () => {
    if ($daemonConfig === null) {
      try {
        const cfg = await fetchConfig();
        daemonConfig.set(cfg);
      } catch { /* daemon might not be up on first render */ }
    }
    configLoaded = true;
  });

  async function handleQuit() {
    try {
      await quitDaemon();
    } catch { }
  }

  async function refreshServerHealth() {
    try {
      const h = await fetchServerHealth();
      serverHealth.set(h);
    } catch { }
  }

  function openServerWeb() {
    const cfg = $daemonConfig;
    if (cfg) {
      window.open(cfg.server_web_url, '_blank');
    }
  }
</script>

<aside class="flex flex-col w-44 bg-deep-900 border-r border-deep-700/50 flex-shrink-0 relative z-10 overflow-hidden">
  <div class="ambient-glow"></div>
  <FlameLayer />

  <div class="flex items-center gap-2.5 px-4 h-11 border-b border-deep-700/50 shrink-0 relative z-10">
    <div class="w-4 h-4 bg-ember-500 shrink-0" style="box-shadow: 0 0 12px rgba(251,146,60,0.5);"></div>
    <span class="text-white font-bold text-sm uppercase tracking-widest">Bonfire</span>
  </div>

  <nav class="flex-1 py-2 relative z-10">
    {#each navItems as item}
      <button
        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-all border-l-2 uppercase tracking-wider font-medium
          {$currentView === item.id
            ? 'bg-ember-500/10 border-ember-400 text-ember-300'
            : 'border-transparent text-deep-300 hover:bg-deep-800/50 hover:border-deep-500 hover:text-deep-100'}"
        onclick={() => currentView.set(item.id)}
      >
        <span class="text-lg">{item.icon}</span>
        <span>{item.label}</span>
      </button>
    {/each}
  </nav>

  <div class="p-3 border-t border-deep-700/30 space-y-2 relative z-10">
    <div class="flex items-center gap-2.5">
      <span
        class="w-2 h-2 rounded-full shrink-0"
        class:bg-emerald-400={isOnline} class:shadow-[0_0_8px_rgba(52,211,153,0.6)]={isOnline}
        class:bg-deep-500={!isOnline}
      ></span>
      <span class="text-xs uppercase tracking-wider" class:text-emerald-400={isOnline} class:text-deep-400={!isOnline}>
        {isOnline ? 'Online' : 'Offline'}
      </span>
    </div>

    <button
      onclick={openServerWeb}
      class="w-full flex items-center gap-2 px-3 py-1.5 text-xs uppercase tracking-wider font-medium
        text-deep-300 hover:text-white bg-deep-800/50 hover:bg-emerald-700/30
        border border-deep-700/50 hover:border-emerald-600/30 transition-all"
    >
      <span class="w-1.5 h-1.5 rounded-full"
        class:bg-emerald-400={$serverHealth?.connected}
        class:bg-deep-500={!$serverHealth?.connected}
      ></span>
      Server
    </button>

    <button
      onclick={handleQuit}
      class="w-full px-3 py-1.5 text-xs uppercase tracking-wider font-medium text-deep-300
        hover:text-white bg-deep-800/50 hover:bg-flame-700/40 border border-deep-700/50
        hover:border-flame-600/40 transition-all"
    >
      Quit
    </button>
  </div>
</aside>
