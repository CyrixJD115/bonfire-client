<script lang="ts">
  import { serverUrl } from '../../stores';

  let localServerUrl = $serverUrl;

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
</script>

<div class="max-w-lg space-y-6">
  <h1 class="text-2xl font-bold text-white uppercase tracking-wider"
    style="text-shadow: 0 0 30px rgba(251,146,60,0.2);">
    Settings
  </h1>

  <div class="bg-deep-800/80 border border-deep-600/50 p-5 shadow-block shadow-black/40 backdrop-blur-sm rounded-none">
    <h3 class="text-base font-bold text-white uppercase tracking-wider border-b border-deep-600/30 pb-2 mb-4"
      style="text-shadow: 0 0 20px rgba(251,146,60,0.15);">
      Server Connection
    </h3>
    <div class="space-y-3">
      <label class="block">
        <span class="text-xs uppercase tracking-wider text-deep-200 font-semibold">Bonfire Server URL</span>
        <input
          type="text"
          bind:value={localServerUrl}
          class="mt-1 w-full bg-deep-900 border border-deep-600/50 px-3 py-2.5 text-deep-50 font-mono text-sm
            focus:outline-none focus:border-ember-500 focus:shadow-glow-amber transition-shadow"
          placeholder="http://localhost:8383"
        />
      </label>
      <button
        onclick={saveSettings}
        class="px-5 py-2.5 font-semibold text-sm uppercase tracking-wider text-white
          bg-ember-600 hover:bg-ember-500 border border-ember-400/30
          shadow-block shadow-black/40
          active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_0px_rgba(0,0,0,0.6)]
          transition-all"
      >
        Save
      </button>
    </div>
  </div>
</div>
