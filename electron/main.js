const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

// Start the Python backend server
function startBackend() {
    const isDev = !app.isPackaged;

    if (isDev) {
        // In development, assume backend is running separately
        console.log('Development mode: Backend should be started separately');
        return null;
    }

    // In production, start the bundled backend
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    const backendPath = path.join(process.resourcesPath, 'backend');

    console.log('Starting backend server...');

    backendProcess = spawn(pythonPath, [
        '-m', 'uvicorn',
        'app.main:app',
        '--host', '127.0.0.1',
        '--port', '8000'
    ], {
        cwd: backendPath,
        env: { ...process.env }
    });

    backendProcess.stdout.on('data', (data) => {
        console.log(`Backend: ${data}`);
    });

    backendProcess.stderr.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
    });

    return backendProcess;
}

// Create the main window
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        title: 'Market Oracle',
        icon: path.join(__dirname, 'assets', 'icon.png'),
        backgroundColor: '#0a0a14',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        titleBarStyle: 'hiddenInset',
        frame: process.platform !== 'darwin',
        show: false
    });

    // Load the app
    const isDev = !app.isPackaged;

    if (isDev) {
        // Development: Load from Vite dev server
        mainWindow.loadURL('http://localhost:5173');
        mainWindow.webContents.openDevTools();
    } else {
        // Production: Load from backend server serving static files
        // Wait for backend to start
        setTimeout(() => {
            mainWindow.loadURL('http://localhost:8000');
        }, 3000);
    }

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Open external links in browser
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// App lifecycle
app.whenReady().then(() => {
    startBackend();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    // Kill backend process
    if (backendProcess) {
        backendProcess.kill();
    }

    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
});

// Security: Disable navigation to unknown URLs
app.on('web-contents-created', (event, contents) => {
    contents.on('will-navigate', (event, navigationUrl) => {
        const parsedUrl = new URL(navigationUrl);
        if (parsedUrl.origin !== 'http://localhost:8000' && parsedUrl.origin !== 'http://localhost:5173') {
            event.preventDefault();
        }
    });
});
