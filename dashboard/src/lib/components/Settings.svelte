<script lang="ts">
  import { onMount } from 'svelte';
  import { serverUrl, daemonConfig } from '../../stores';
  import { fetchConfig } from '../../api';

  let localServerUrl = $serverUrl;
  let daemonInfo = $daemonConfig;

  onMount(async () => {
    try {
      const cfg = await fetchConfig();
      daemonConfig.set(cfg);
      daemonInfo = cfg;
      if (!localServerUrl || localServerUrl === 'http://localhost:8383') {
        localServerUrl = cfg.server_web_url;
        serverUrl.set(cfg.server_web_url);
      }
    } catch { }
  });

  function saveSettings() {
    serverUrl.set(localServerUrl);
    localStorage.setItem('bonfire-server-url', localServerUrl);
  }

  function restoreSaved() {
    const saved = localStorage.getItem('bonfire-server-url');
    if (saved) {
      serverUrl.set(saved);
      localServerUrl = saved;
    }
  }

  restoreSaved();

  $: serverUrlDisplay = localServerUrl;
</script>

<div class="min-h-full flex items-center justify-center">
  <div class="w-full max-w-lg space-y-6">
  <h1 class="text-2xl font-bold text-white uppercase tracking-wider"
    style="text-shadow: 0 0 30px rgba(251,146,60,0.2);">
    Settings
  </h1>

  <div class="card">
    <h3 class="card-header">Server Connection</h3>
    <div class="space-y-3">
      <label class="block">
        <span class="text-xs uppercase tracking-wider text-deep-200 font-semibold">Bonfire Server Web URL</span>
        <input
          type="text"
          bind:value={localServerUrl}
          class="input mt-1"
          placeholder="http://localhost:17755"
        />
      </label>
      <button onclick={saveSettings} class="btn btn-primary">Save</button>
    </div>
  </div>

  {#if daemonInfo}
    <div class="card">
      <h3 class="card-header">Daemon Configuration</h3>
      <div class="space-y-2 text-xs">
        <div class="flex justify-between">
          <span class="text-deep-400 uppercase tracking-wider">Server</span>
          <span class="text-deep-200">{daemonInfo.server_url}:{daemonInfo.server_port}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-deep-400 uppercase tracking-wider">Machine ID</span>
          <span class="text-deep-200 font-mono">{daemonInfo.machine_id}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-deep-400 uppercase tracking-wider">Web URL</span>
          <span class="text-ember-300">{daemonInfo.server_web_url}</span>
        </div>
      </div>
    </div>
  {/if}
  </div>
</div>
