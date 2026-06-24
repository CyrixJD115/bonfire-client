interface Window {
  bonfire: {
    daemon: {
      health: () => Promise<{ status: string; uptime: string; version: string }>;
      scan: () => Promise<{ games_found: number; save_files: number; last_scan: string; errors: string[] }>;
      status: () => Promise<{ games_found: number; save_files: number; last_scan: string; errors: string[] }>;
    };
  };
}
