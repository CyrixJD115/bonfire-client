const DAEMON_BASE = 'http://127.0.0.1:21466';

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${DAEMON_BASE}${path}`);
  if (!res.ok) throw new Error(`Daemon error: ${res.status} ${res.statusText}`);
  return res.json();
}

export function fetchHealth() {
  return apiGet<{ status: string; uptime: string; version: string }>('/api/health');
}

export function fetchStatus() {
  return apiGet<{ games_found: number; save_files: number; last_scan: string; errors: string[] }>('/api/status');
}

export function triggerScan() {
  return apiGet<{ games_found: number; save_files: number; last_scan: string; errors: string[] }>('/api/scan');
}
