const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const chokidar = require('chokidar');

// Disable GPU acceleration
app.disableHardwareAcceleration();

let mainWindow;
let fileWatcher = null;
let fileChanges = [];

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: false
    },
    titleBarStyle: 'hidden',
    frame: false,
    backgroundColor: '#ffffff'
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  
  // Always open DevTools in development
  mainWindow.webContents.openDevTools();
}

function startFileWatching() {
  if (fileWatcher) {
    fileWatcher.close();
  }

  const homeDir = process.env.HOME || process.env.USERPROFILE;
  fileWatcher = chokidar.watch(homeDir, {
    ignored: [
      /(^|[\/\\])\../, // ignore dotfiles
      '**/node_modules/**',
      '**/.git/**',
      '**/tmp/**',
      '**/temp/**',
      '**/cache/**',
      '**/Cache/**',
      '**/.cache/**',
      '**/SecureWorkspace/**'
    ],
    persistent: true,
    ignoreInitial: true
  });

  fileWatcher
    .on('add', path => {
      const change = {
        path,
        type: 'new',
        timestamp: Date.now()
      };
      fileChanges.push(change);
      if (mainWindow) {
        mainWindow.webContents.send('file-changes-updated', fileChanges);
      }
    })
    .on('change', path => {
      const change = {
        path,
        type: 'modified',
        timestamp: Date.now()
      };
      fileChanges.push(change);
      if (mainWindow) {
        mainWindow.webContents.send('file-changes-updated', fileChanges);
      }
    })
    .on('unlink', path => {
      const change = {
        path,
        type: 'deleted',
        timestamp: Date.now()
      };
      fileChanges.push(change);
      if (mainWindow) {
        mainWindow.webContents.send('file-changes-updated', fileChanges);
      }
    });
}

function stopFileWatching() {
  if (fileWatcher) {
    fileWatcher.close();
    fileWatcher = null;
  }
  fileChanges = [];
}

app.whenReady().then(() => {
  createWindow();
  startFileWatching();
});

app.on('window-all-closed', () => {
  stopFileWatching();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC handlers for secure workspace operations
ipcMain.handle('toggle-secure-mode', async (event, enabled, selectedFiles = []) => {
  try {
    const scriptPath = path.join(__dirname, '..', '..', enabled ? 'start_session.py' : 'stop_session.py');
    console.log('Executing script:', scriptPath);
    
    // Check if script exists
    if (!fs.existsSync(scriptPath)) {
      console.error('Script not found:', scriptPath);
      return { success: false, error: 'Script not found' };
    }

    const pythonProcess = spawn('python3', [
      scriptPath,
      ...(enabled ? [] : ['--preserve-files', JSON.stringify(selectedFiles)])
    ]);
    
    return new Promise((resolve, reject) => {
      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
        console.log('Python stdout:', data.toString());
      });

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
        console.error('Python stderr:', data.toString());
      });

      pythonProcess.on('close', (code) => {
        console.log('Python process exited with code:', code);
        if (code === 0) {
          if (enabled) {
            startFileWatching();
          } else {
            stopFileWatching();
          }
          resolve({ success: true });
        } else {
          resolve({ 
            success: false, 
            error: `Process exited with code ${code}`,
            stdout,
            stderr
          });
        }
      });
      
      pythonProcess.on('error', (err) => {
        console.error('Failed to execute Python script:', err);
        reject({ 
          success: false, 
          error: err.message,
          stdout,
          stderr
        });
      });
    });
  } catch (error) {
    console.error('Error in toggle-secure-mode:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-file-changes', async () => {
  return fileChanges;
}); 