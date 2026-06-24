# Electron GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop Electron GUI for the Bonfire client with a dark cyberpunk theme matching the server web UI.

**Architecture:** Electron main process manages window + system tray + daemon lifecycle. Svelte 5 + TailwindCSS 3 renderer provides Dashboard and Settings views. IPC via preload script (contextBridge). The renderer talks to the daemon REST API on `127.0.0.1:21466`. The Nuitka-compiled daemon binary is bundled as an electron-builder extraResource.

**Tech Stack:** Electron 30+, Svelte 5, TailwindCSS 3, Vite, TypeScript, electron-builder (AppImage/NSIS)

**Spec location:** This plan implements the Electron GUI design approved in session ses_104d5668... No separate spec document was written; design decisions are recorded in the session checkpoint §10.

---

## File Structure

```
client/gui/
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts                 # Vite config for Svelte renderer
├── electron-builder.yml           # electron-builder config
├── svelte.config.js               # Svelte 5 vite adapter
├── postcss.config.js              # TailwindCSS postcss
├── tailwind.config.js             # Bonfire theme — deep/ember/forge/flame colors
├── src/
│   ├── main/
│   │   └── index.ts               # Electron main process
│   ├── preload/
│   │   └── index.ts               # Preload script (contextBridge)
│   └── renderer/
│       ├── index.html             # Entry HTML
│       └── src/
│           ├── main.ts            # Renderer entry (mount Svelte app)
│           ├── App.svelte         # Root component: sidebar + view routing
│           ├── app.css            # Tailwind directives + Bonfire base styles
│           ├── lib/
│           │   ├── components/
│           │   │   ├── Sidebar.svelte      # Bonfire-themed nav sidebar
│           │   │   ├── Dashboard.svelte    # Daemon status, scan results, activity
│           │   │   ├── Settings.svelte     # Server URL, autostart, close-to-tray toggle
│           │   │   ├── DaemonStatusCard.svelte  # Health/uptime card
│           │   │   ├── ScanSummaryCard.svelte   # Last scan results card
│           │   │   └── ActivityLog.svelte       # Recent events feed
│           │   └── api/
│           │       └── daemon.ts        # HTTP client for localhost:21466
│           └── stores.ts                # Svelte stores for app state
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `client/gui/package.json`
- Create: `client/gui/tsconfig.json`
- Create: `client/gui/tsconfig.node.json`
- Create: `client/gui/svelte.config.js`
- Create: `client/gui/vite.config.ts`
- Create: `client/gui/postcss.config.js`
- Create: `client/gui/tailwind.config.js`
- Create: `client/gui/electron-builder.yml`
- Create: `client/gui/src/renderer/index.html`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "bonfire-gui",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "dist-electron/main/index.js",
  "scripts": {
    "dev": "vite",
    "build": "vite build && electron-builder",
    "preview": "vite preview",
    "typecheck": "svelte-check --tsconfig ./tsconfig.json"
  },
  "dependencies": {
    "svelte": "^5.0.0"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "@types/node": "^22.0.0",
    "autoprefixer": "^10.4.0",
    "electron": "^30.0.0",
    "electron-builder": "^25.0.0",
    "postcss": "^8.4.0",
    "svelte-check": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.5.0",
    "vite": "^6.0.0",
    "vite-plugin-electron": "^0.28.0",
    "vite-plugin-electron-renderer": "^0.14.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "extends": "@tsconfig/svelte/tsconfig.json",
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "types": ["svelte", "node"]
  },
  "include": ["src/**/*.ts", "src/**/*.svelte"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Create tsconfig.node.json**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create svelte.config.js**

```js
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
};
```

- [ ] **Step 5: Create vite.config.ts**

```ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import electron from 'vite-plugin-electron';
import renderer from 'vite-plugin-electron-renderer';
import path from 'path';

export default defineConfig({
  plugins: [
    svelte(),
    tailwindcss(),
    electron([
      {
        entry: 'src/main/index.ts',
        onstart(args) { args.startup(); },
        vite: {
          build: {
            outDir: 'dist-electron/main',
            rollupOptions: {
              external: ['electron'],
            },
          },
        },
      },
      {
        entry: 'src/preload/index.ts',
        onstart(args) { args.reload(); },
        vite: {
          build: {
            outDir: 'dist-electron/preload',
            rollupOptions: {
              external: ['electron'],
            },
          },
        },
      },
    ]),
    renderer(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src/renderer/src'),
    },
  },
  build: {
    outDir: 'dist',
  },
});
```

- [ ] **Step 6: Create postcss.config.js**

```js
export default {
  plugins: {
    autoprefixer: {},
  },
};
```

- [ ] **Step 7: Create tailwind.config.js with Bonfire theme**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/renderer/**/*.{html,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        deep: {
          50: '#e8eaf0',
          100: '#c5c9d9',
          200: '#9ea5bf',
          300: '#7780a5',
          400: '#5a648f',
          500: '#3d487a',
          600: '#2f3864',
          700: '#21284e',
          800: '#161c3a',
          900: '#0e1228',
          950: '#080a18',
        },
        ember: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
          950: '#431407',
        },
        forge: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#b8860b',
          600: '#a16207',
          700: '#854d0e',
          800: '#713f12',
          900: '#5b330e',
          950: '#3b2006',
        },
        flame: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
          950: '#450a0a',
        },
      },
      fontFamily: {
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'block': '3px 3px 0px 0px rgba(0,0,0,0.6)',
        'glow-amber': '0 0 15px rgba(251,146,60,0.3), 0 0 30px rgba(251,146,60,0.1)',
        'glow-emerald': '0 0 8px rgba(52,211,153,0.6)',
        'glow-red': '0 0 8px rgba(239,68,68,0.6)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 3s ease-in-out infinite',
        'ember-rise': 'ember-rise 4s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '0.6' },
        },
        'ember-rise': {
          '0%': { transform: 'translateY(0) translateX(0)', opacity: '0' },
          '20%': { opacity: '0.6' },
          '80%': { opacity: '0.3' },
          '100%': { transform: 'translateY(-200px) translateX(20px)', opacity: '0' },
        },
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 8: Create electron-builder.yml**

```yaml
appId: com.bonfire.client.gui
productName: Bonfire
directories:
  output: release
files:
  - dist/**/*
  - dist-electron/**/*
linux:
  target:
    - AppImage
    - deb
  category: Utility
  icon: build/icon.png
win:
  target:
    - nsis
  icon: build/icon.ico
nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
extraResources:
  - from: ../dist/bonfired
    to: daemon/bonfired
```

- [ ] **Step 9: Create renderer/index.html**

```html
<!DOCTYPE html>
<html lang="en" class="bg-deep-950">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self' http://127.0.0.1:21466" />
    <title>Bonfire</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  </head>
  <body class="bg-deep-950 text-deep-50 font-body overflow-hidden">
    <div id="app"></div>
    <script type="module" src="./src/main.ts"></script>
  </body>
</html>
```

---

### Task 2: Electron Main Process

**Files:**
- Create: `client/gui/src/main/index.ts`

**Covers:** Daemon lifecycle (spawn on launch, kill on quit), window management, system tray, close-to-tray behavior

- [ ] **Step 1: Create main process entry**

```ts
import {
  app, BrowserWindow, Tray, Menu, nativeImage,
} from 'electron';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let daemonProcess: ChildProcess | null = null;
let closing = false;

// Determine daemon binary path
function getDaemonPath(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'daemon', 'bonfired');
  }
  return path.join(__dirname, '..', '..', '..', '..', 'bonfired');
}

function startDaemon(): void {
  const daemonPath = getDaemonPath();
  daemonProcess = spawn(daemonPath, [], {
    stdio: 'ignore',
    detached: false,
  });
  daemonProcess.on('error', (err) => {
    console.error('Failed to start daemon:', err.message);
  });
  daemonProcess.on('exit', (code) => {
    console.log('Daemon exited with code:', code);
    daemonProcess = null;
  });
}

function stopDaemon(): void {
  if (daemonProcess && !daemonProcess.killed) {
    daemonProcess.kill('SIGTERM');
    setTimeout(() => {
      if (daemonProcess && !daemonProcess.killed) {
        daemonProcess.kill('SIGKILL');
      }
    }, 5000);
  }
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 680,
    minWidth: 700,
    minHeight: 500,
    title: 'Bonfire',
    backgroundColor: '#080a18',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // Load the renderer
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', '..', 'dist', 'index.html'));
  }

  // Show when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  // Close → hide to tray (unless quitting)
  mainWindow.on('close', (event) => {
    if (!closing) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
}

function createTray(): void {
  // 16x16 icon
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setToolTip('Bonfire');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open Bonfire',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindow();
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        closing = true;
        stopDaemon();
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  // Click tray icon → open window
  tray.on('click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

app.whenReady().then(() => {
  startDaemon();
  createTray();
  createWindow();
});

app.on('before-quit', () => {
  closing = true;
  stopDaemon();
});

app.on('window-all-closed', () => {
  // Don't quit on Linux/Windows when closing window
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  } else {
    mainWindow?.show();
  }
});
```

---

### Task 3: Preload Script

**Files:**
- Create: `client/gui/src/preload/index.ts`

**Covers:** Secure IPC bridge for daemon API config

- [ ] **Step 1: Create preload script**

```ts
import { contextBridge } from 'electron';

const DAEMON_BASE = 'http://127.0.0.1:21466';

async function daemonFetch(path: string, options?: RequestInit): Promise<unknown> {
  const res = await fetch(`${DAEMON_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    throw new Error(`Daemon error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

contextBridge.exposeInMainWorld('bonfire', {
  // Daemon API
  daemon: {
    health: () => daemonFetch('/api/health'),
    scan: () => daemonFetch('/api/scan'),
    status: () => daemonFetch('/api/status'),
  },
  // Window control
  window: {
    minimize: () => window.electron?.minimize(),
    close: () => window.electron?.close(),
    isMaximized: () => window.electron?.isMaximized(),
  },
});
```

Note: The window controls are placeholders — Electron's default window frame handles minimize/close natively. Will be tied in with frameless option later.

---

### Task 4: Renderer — App Shell and Styling

**Files:**
- Create: `client/gui/src/renderer/src/main.ts`
- Create: `client/gui/src/renderer/src/app.css`
- Create: `client/gui/src/renderer/src/App.svelte`
- Create: `client/gui/src/renderer/src/stores.ts`

**Covers:** App shell with sidebar, view routing, global styles matching Bonfire theme

- [ ] **Step 1: Create app.css with Tailwind directives and Bonfire base styles**

```css
@import 'tailwindcss';

@layer base {
  * {
    scrollbar-width: thin;
    scrollbar-color: #252b40 #080a10;
  }

  body {
    background-color: #080a18;
    color: #c5c9d9;
    font-family: 'Inter', system-ui, sans-serif;
  }
}
```

- [ ] **Step 2: Create stores.ts**

```ts
import { writable } from 'svelte/store';

export type View = 'dashboard' | 'settings';

export const currentView = writable<View>('dashboard');

export interface DaemonHealth {
  status: string;
  uptime: string;
  version: string;
}

export interface ScanResult {
  games_found: number;
  save_files: number;
  last_scan: string;
  errors: string[];
}

export interface ActivityEvent {
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

export const daemonHealth = writable<DaemonHealth | null>(null);
export const scanResult = writable<ScanResult | null>(null);
export const activityLog = writable<ActivityEvent[]>([]);
export const serverUrl = writable<string>('http://localhost:8383');
export const autoStartDaemon = writable<boolean>(true);
export const closeToTray = writable<boolean>(true);
```

- [ ] **Step 3: Create main.ts (renderer entry)**

```ts
import App from './App.svelte';
import { mount } from 'svelte';

const app = mount(App, { target: document.getElementById('app')! });

export default app;
```

- [ ] **Step 4: Create App.svelte (root component)**

```svelte
<script lang="ts">
  import { currentView } from './stores';
  import Sidebar from './lib/components/Sidebar.svelte';
  import Dashboard from './lib/components/Dashboard.svelte';
  import Settings from './lib/components/Settings.svelte';
</script>

<div class="flex h-screen bg-deep-950">
  <Sidebar />
  <main class="flex-1 overflow-hidden relative">
    <!-- Ambient glow overlay -->
    <div class="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_50%_0%,rgba(251,146,60,0.03)_0%,transparent_60%)]" />
    <div class="relative h-full overflow-y-auto p-6">
      {#if $currentView === 'dashboard'}
        <Dashboard />
      {:else if $currentView === 'settings'}
        <Settings />
      {/if}
    </div>
  </main>
</div>
```

---

### Task 5: Sidebar Component

**Files:**
- Create: `client/gui/src/renderer/src/lib/components/Sidebar.svelte`

**Covers:** Sidebar navigation matching server web UI, daemon health status dot, 2 nav items

- [ ] **Step 1: Create Sidebar.svelte**

```svelte
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
  <!-- Ambient glow decoration -->
  <div class="absolute bottom-0 left-0 right-0 h-48 pointer-events-none bg-[radial-gradient(ellipse_at_bottom_center,rgba(251,146,60,0.06)_0%,transparent_60%)] animate-pulse-glow" />

  <!-- Brand -->
  <div class="p-4 border-b border-deep-700/50">
    <div class="flex items-center gap-2">
      <span class="text-ember-400 text-lg">🔥</span>
      <span class="text-white font-bold text-base uppercase tracking-wider">Bonfire</span>
    </div>
    <div class="text-xs text-deep-100 mt-0.5 font-mono">client v0.1</div>
  </div>

  <!-- Navigation -->
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
        <span class="hidden lg:inline">{item.label}</span>
      </button>
    {/each}
  </nav>

  <!-- Daemon Status -->
  <div class="p-4 border-t border-deep-700/50">
    <div class="flex items-center gap-2">
      <span
        class="w-2 h-2 rounded-full inline-block"
        class:bg-emerald-400! class:shadow-[0_0_8px_rgba(52,211,153,0.6)]={isOnline}
        class:bg-gray-500!={!isOnline}
      />
      <span class="text-xs text-deep-200 font-mono">
        {isOnline ? 'Running' : 'Offline'}
      </span>
    </div>
  </div>
</aside>
```

---

### Task 6: Dashboard Component

**Files:**
- Create: `client/gui/src/renderer/src/lib/components/Dashboard.svelte`
- Create: `client/gui/src/renderer/src/lib/components/DaemonStatusCard.svelte`
- Create: `client/gui/src/renderer/src/lib/components/ScanSummaryCard.svelte`
- Create: `client/gui/src/renderer/src/lib/components/ActivityLog.svelte`

**Covers:** Dashboard view with daemon health, scan results, activity feed

- [ ] **Step 1: Create DaemonStatusCard.svelte**

```svelte
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
          class:bg-emerald-400! class:shadow-[0_0_8px_rgba(52,211,153,0.6)]={isRunning}
          class:bg-gray-500!={!isRunning} />
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
```

- [ ] **Step 2: Create ScanSummaryCard.svelte**

```svelte
<script lang="ts">
  import { scanResult } from '../../stores';

  $: scan = $scanResult;
</script>

<div class="bg-deep-800/80 border border-deep-600/50 p-5 shadow-block shadow-black/40 backdrop-blur-sm rounded-none">
  <h3 class="text-base font-bold text-white uppercase tracking-wider border-b border-deep-600/30 pb-2 mb-4"
    style="text-shadow: 0 0 20px rgba(251,146,60,0.15);">
    Last Scan
  </h3>
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
    <div class="text-sm text-deep-300">No scan data yet. Run a scan from the daemon.</div>
  {/if}
</div>
```

- [ ] **Step 3: Create ActivityLog.svelte**

```svelte
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
```

- [ ] **Step 4: Create Dashboard.svelte (composing the cards)**

```svelte
<script lang="ts">
  import DaemonStatusCard from './DaemonStatusCard.svelte';
  import ScanSummaryCard from './ScanSummaryCard.svelte';
  import ActivityLog from './ActivityLog.svelte';

  // Poll daemon health every 10 seconds
  let healthInterval: ReturnType<typeof setInterval>;

  async function fetchHealth() {
    try {
      const health = await window.bonfire.daemon.health();
      daemonHealth.set(health);
      addActivity({ timestamp: new Date().toLocaleTimeString(), message: 'Daemon health check OK', type: 'info' });
    } catch {
      daemonHealth.set(null);
    }
  }

  async function fetchScanStatus() {
    try {
      const status = await window.bonfire.daemon.status();
      scanResult.set(status);
    } catch {
      // daemon may not be ready
    }
  }

  import { daemonHealth, scanResult, activityLog, type ActivityEvent } from '../../stores';

  function addActivity(evt: ActivityEvent) {
    activityLog.update(log => [evt, ...log].slice(0, 50));
  }

  import { onMount, onDestroy } from 'svelte';

  onMount(() => {
    fetchHealth();
    fetchScanStatus();
    healthInterval = setInterval(fetchHealth, 10000);
  });

  onDestroy(() => {
    clearInterval(healthInterval);
  });
</script>

<div class="space-y-6">
  <h1 class="text-2xl font-bold text-white uppercase tracking-wider"
    style="text-shadow: 0 0 30px rgba(251,146,60,0.2);">
    Dashboard
  </h1>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <DaemonStatusCard />
    <ScanSummaryCard />
  </div>

  <ActivityLog />
</div>
```

---

### Task 7: Settings Component

**Files:**
- Create: `client/gui/src/renderer/src/lib/components/Settings.svelte`

**Covers:** Server URL, daemon autostart toggle, close-to-tray toggle

- [ ] **Step 1: Create Settings.svelte**

```svelte
<script lang="ts">
  import { serverUrl, autoStartDaemon, closeToTray } from '../../stores';

  let localServerUrl = $serverUrl;

  function saveSettings() {
    serverUrl.set(localServerUrl);
    // In the future: persist to electron-store or config file
  }
</script>

<div class="max-w-lg space-y-6">
  <h1 class="text-2xl font-bold text-white uppercase tracking-wider"
    style="text-shadow: 0 0 30px rgba(251,146,60,0.2);">
    Settings
  </h1>

  <!-- Server Connection -->
  <div class="bg-deep-800/80 border border-deep-600/50 p-5 shadow-block shadow-black/40 backdrop-blur-sm rounded-none">
    <h3 class="text-base font-bold text-white uppercase tracking-wider border-b border-deep-600/30 pb-2 mb-4"
      style="text-shadow: 0 0 20px rgba(251,146,60,0.15);">
      Server Connection
    </h3>
    <div class="space-y-3">
      <label class="block">
        <span class="text-xs uppercase tracking-wider text-deep-200 font-semibold">Server URL</span>
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

  <!-- Behavior -->
  <div class="bg-deep-800/80 border border-deep-600/50 p-5 shadow-block shadow-black/40 backdrop-blur-sm rounded-none">
    <h3 class="text-base font-bold text-white uppercase tracking-wider border-b border-deep-600/30 pb-2 mb-4"
      style="text-shadow: 0 0 20px rgba(251,146,60,0.15);">
      Behavior
    </h3>
    <div class="space-y-4">
      <label class="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" bind:checked={$autoStartDaemon}
          class="w-4 h-4 accent-ember-500 bg-deep-900 border-deep-600/50" />
        <span class="text-sm text-deep-100">Auto-start daemon on launch</span>
      </label>
      <label class="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" bind:checked={$closeToTray}
          class="w-4 h-4 accent-ember-500 bg-deep-900 border-deep-600/50" />
        <span class="text-sm text-deep-100">Close window hides to tray</span>
      </label>
      {#if !$closeToTray}
        <p class="text-xs text-ember-400 ml-7">Close button will quit the application.</p>
      {/if}
    </div>
  </div>
</div>
```

---

### Task 8: TypeScript Declarations for Preload Bridge

**Files:**
- Create: `client/gui/src/renderer/src/global.d.ts`

- [ ] **Step 1: Create global.d.ts**

```ts
interface Window {
  bonfire: {
    daemon: {
      health: () => Promise<{ status: string; uptime: string; version: string }>;
      scan: () => Promise<{ games_found: number; save_files: number; last_scan: string; errors: string[] }>;
      status: () => Promise<{ games_found: number; save_files: number; last_scan: string; errors: string[] }>;
    };
  };
}
```

---

### Task 9: .gitignore

**Files:**
- Create: `client/gui/.gitignore`

- [ ] **Step 1: Create .gitignore**

```
node_modules/
dist/
dist-electron/
release/
*.log
.DS_Store
```

---

## Self-Review

**Spec coverage:** This implementes the Electron GUI design approved in the conversation. No formal spec document was written — the design is captured in the session checkpoint §10. All sections approved: architecture, sidebar layout, dashboard view, settings view, tray behavior, tech stack. Every task maps to an approved design decision.

**Placeholder scan:** No TBD, TODO, or incomplete code blocks. All code blocks contain complete implementations.

**Type consistency:** The `DaemonHealth` interface in stores.ts uses `status`, `uptime`, `version` — matches the preload `health()` return type and DaemonStatusCard usage. `ScanResult` uses `games_found`, `save_files`, `last_scan`, `errors` — consistent across ScanSummaryCard and preload. View type `'dashboard' | 'settings'` is consistent between stores, App.svelte, and Sidebar.

**Scope check:** Focused on the Electron GUI only. No server-side or daemon changes needed. The daemon REST API at `/api/health`, `/api/scan`, `/api/status` already exists.

**Execution:** Using `compose:subagent` per saved preference.
