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
