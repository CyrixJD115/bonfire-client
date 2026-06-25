import { writable } from 'svelte/store';

export type View = 'dashboard' | 'games' | 'settings';

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

export interface ServerHealth {
  connected: boolean;
  server_version: string;
}

export interface DaemonConfig {
  server_url: string;
  server_port: number;
  api_key: string;
  machine_id: string;
  server_web_url: string;
}

export const daemonHealth = writable<DaemonHealth | null>(null);
export const scanResult = writable<ScanResult | null>(null);
export const activityLog = writable<ActivityEvent[]>([]);
export const serverUrl = writable<string>('http://localhost:8383');
export const games = writable<GameEntry[]>([]);
export const serverHealth = writable<ServerHealth | null>(null);
export const daemonConfig = writable<DaemonConfig | null>(null);
