const DAEMON_BASE = 'http://127.0.0.1:21466';

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${DAEMON_BASE}${path}`);
  if (!res.ok) throw new Error(`Daemon error: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function apiPost<T>(path: string): Promise<T> {
  const res = await fetch(`${DAEMON_BASE}${path}`, { method: 'POST' });
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

export function quitDaemon() {
  return apiPost<{ status: string }>('/shutdown');
}

export interface GameEntry {
  id: string;
  title: string;
  platform: string;
  storefront: string;
  save_dir: string | null;
  file_count: number;
  sync_status: string;
  local_hash: string;
  install_path: string | null;
  has_save_files: boolean;
}

export function fetchGames() {
  return apiGet<{ games: GameEntry[] }>('/api/games');
}

export interface DaemonConfigResponse {
  server_url: string;
  server_port: number;
  api_key: string;
  machine_id: string;
  server_web_url: string;
}

export function fetchConfig() {
  return apiGet<DaemonConfigResponse>('/api/config');
}

export interface ServerHealthResponse {
  connected: boolean;
  server_version: string;
}

export function fetchServerHealth() {
  return apiGet<ServerHealthResponse>('/api/server-health');
}
