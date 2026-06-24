import {
  app, BrowserWindow, Tray, Menu, nativeImage,
} from 'electron';
import { spawn } from 'child_process';
import type { ChildProcess } from 'child_process';
import path from 'path';

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let daemonProcess: ChildProcess | null = null;
let closing = false;

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

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', '..', 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  mainWindow.on('close', (event) => {
    if (!closing) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
}

function createTray(): void {
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
