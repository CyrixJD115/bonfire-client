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
  daemon: {
    health: () => daemonFetch('/api/health'),
    scan: () => daemonFetch('/api/scan'),
    status: () => daemonFetch('/api/status'),
  },
});
