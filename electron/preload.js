// Preload script for Electron
// Exposes safe APIs to the renderer process

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
    // App info
    getVersion: () => process.env.npm_package_version || '1.0.0',
    getPlatform: () => process.platform,

    // Window controls
    minimizeWindow: () => ipcRenderer.send('minimize-window'),
    maximizeWindow: () => ipcRenderer.send('maximize-window'),
    closeWindow: () => ipcRenderer.send('close-window'),

    // System notifications
    showNotification: (title, body) => {
        new Notification(title, { body });
    }
});

console.log('Market Oracle Electron preload script loaded');
