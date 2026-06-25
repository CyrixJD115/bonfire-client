<script lang="ts">
  import { currentView } from './stores';
  import Sidebar from './lib/components/Sidebar.svelte';
  import Dashboard from './lib/components/Dashboard.svelte';
  import GamesView from './lib/components/GamesView.svelte';
  import Settings from './lib/components/Settings.svelte';
</script>

<div class="flex h-screen bg-deep-950">
  <Sidebar />
  <main class="flex-1 overflow-hidden relative">
    <div class="relative h-full overflow-y-auto p-6">
      {#if $currentView === 'dashboard'}
        <Dashboard />
      {:else if $currentView === 'games'}
        <GamesView />
      {:else if $currentView === 'settings'}
        <Settings />
      {/if}
    </div>
  </main>
</div>
