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
let sessionHistory = [];
let pythonProcess = null;  // Track the Python process

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

function addToSessionHistory(session) {
  sessionHistory.push({
    ...session,
    timestamp: Date.now()
  });
  if (mainWindow) {
    mainWindow.webContents.send('session-history-updated', sessionHistory);
  }
}

app.whenReady().then(() => {
  createWindow();
  startFileWatching();
});

app.on('window-all-closed', () => {
  stopFileWatching();
  
  // If there's a running Python process, terminate it
  if (pythonProcess) {
    console.log('Terminating Python process...');
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
  
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

    // If disabling secure mode, pause file watching during cleanup
    if (!enabled) {
      stopFileWatching();
    }

    // Convert relative paths to absolute paths for selected files
    const absoluteSelectedFiles = selectedFiles.map(filePath => {
      // If the path is already absolute, return as is
      if (path.isAbsolute(filePath)) {
        return filePath;
      }
      // Otherwise, make it absolute relative to home directory
      return path.join(process.env.HOME || process.env.USERPROFILE, filePath);
    });

    // Store the process reference
    pythonProcess = spawn('python3', [
      scriptPath,
      ...(enabled ? [] : ['--preserve-files', JSON.stringify(absoluteSelectedFiles)])
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
        pythonProcess = null;  // Clear the process reference
        if (code === 0) {
          if (enabled) {
            startFileWatching();
            addToSessionHistory({
              type: 'start',
              timestamp: Date.now()
            });
          } else {
            // Add session end to history
            addToSessionHistory({
              type: 'end',
              preservedFiles: selectedFiles,
              changes: fileChanges,
              timestamp: Date.now()
            });
            fileChanges = [];
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
        pythonProcess = null;  // Clear the process reference
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

ipcMain.handle('get-session-history', async () => {
  return sessionHistory;
}); 