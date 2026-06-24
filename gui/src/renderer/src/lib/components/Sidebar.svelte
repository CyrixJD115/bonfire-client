<script lang="ts">
  import { currentView, daemonHealth, type View } from '../../stores';

  const navItems: { id: View; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '◆' },
    { id: 'settings', label: 'Settings', icon: '⚙' },
  ];

  $: health = $daemonHealth;
  $: isOnline = health?.status === 'running';
</script>

<aside class="flex flex-col w-44 bg-deep-900 border-r border-deep-700/50 flex-shrink-0 relative z-10">
  <div class="absolute bottom-0 left-0 right-0 h-48 pointer-events-none bg-[radial-gradient(ellipse_at_bottom_center,rgba(251,146,60,0.06)_0%,transparent_60%)] animate-pulse-glow" />

  <div class="p-4 border-b border-deep-700/50">
    <div class="flex items-center gap-2">
      <span class="text-ember-400 text-lg">🔥</span>
      <span class="text-white font-bold text-base uppercase tracking-wider">Bonfire</span>
    </div>
    <div class="text-xs text-deep-100 mt-0.5 font-mono">client v0.1</div>
  </div>

  <nav class="flex-1 py-3">
    {#each navItems as item}
      <button
        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors uppercase tracking-wider font-medium
          {$currentView === item.id
            ? 'text-ember-400 bg-ember-500/10 border-r-2 border-ember-500'
            : 'text-deep-200 hover:text-deep-50 hover:bg-deep-800/50'}"
        onclick={() => currentView.set(item.id)}
      >
        <span class="text-lg">{item.icon}</span>
        <span>{item.label}</span>
      </button>
    {/each}
  </nav>

  <div class="p-4 border-t border-deep-700/50">
    <div class="flex items-center gap-2">
      <span
        class="w-2 h-2 rounded-full inline-block"
        class:bg-emerald-400 class:shadow-[0_0_8px_rgba(52,211,153,0.6)]={isOnline}
        class:bg-gray-500={!isOnline}
      />
      <span class="text-xs text-deep-200 font-mono">
        {isOnline ? 'Running' : 'Offline'}
      </span>
    </div>
  </div>
</aside>
