import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import {
  AppBar,
  Toolbar,
  Typography,
  Switch,
  Container,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Box,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Checkbox,
  FormGroup,
  FormControlLabel,
  Divider
} from '@mui/material';
import {
  Security as SecurityIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Save as SaveIcon
} from '@mui/icons-material';
import { createRoot } from 'react-dom/client';

const { ipcRenderer } = window.require('electron');

const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
});

function App() {
  const [secureMode, setSecureMode] = useState(false);
  const [fileChanges, setFileChanges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showFileDialog, setShowFileDialog] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState(new Set());

  useEffect(() => {
    // Initial load of file changes
    loadFileChanges();
    
    // Listen for real-time updates
    ipcRenderer.on('file-changes-updated', (event, changes) => {
      setFileChanges(changes);
    });

    return () => {
      ipcRenderer.removeAllListeners('file-changes-updated');
    };
  }, []);

  const loadFileChanges = async () => {
    try {
      const changes = await ipcRenderer.invoke('get-file-changes');
      setFileChanges(changes);
    } catch (error) {
      console.error('Failed to load file changes:', error);
    }
  };

  const handleSecureModeToggle = async () => {
    if (!secureMode) {
      // When enabling secure mode, just toggle
      setLoading(true);
      try {
        const result = await ipcRenderer.invoke('toggle-secure-mode', true);
        if (result.success) {
          setSecureMode(true);
        } else {
          console.error('Failed to enable secure mode:', result.error);
          alert(`Failed to enable secure mode: ${result.error}\n\nDetails:\n${result.stdout || ''}\n${result.stderr || ''}`);
        }
      } catch (error) {
        console.error('Failed to enable secure mode:', error);
        alert(`Failed to enable secure mode: ${error.message}`);
      }
      setLoading(false);
    } else {
      // When disabling secure mode, show file selection dialog
      setShowFileDialog(true);
    }
  };

  const handleFileSelection = (filePath) => {
    setSelectedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(filePath)) {
        newSet.delete(filePath);
      } else {
        newSet.add(filePath);
      }
      return newSet;
    });
  };

  const handleSaveSelected = async () => {
    setLoading(true);
    try {
      const result = await ipcRenderer.invoke('toggle-secure-mode', false, Array.from(selectedFiles));
      if (result.success) {
        setSecureMode(false);
        setShowFileDialog(false);
        setSelectedFiles(new Set());
      } else {
        console.error('Failed to disable secure mode:', result.error);
        alert(`Failed to disable secure mode: ${result.error}\n\nDetails:\n${result.stdout || ''}\n${result.stderr || ''}`);
      }
    } catch (error) {
      console.error('Failed to disable secure mode:', error);
      alert(`Failed to disable secure mode: ${error.message}`);
    }
    setLoading(false);
  };

  const handleCancel = () => {
    setShowFileDialog(false);
    setSelectedFiles(new Set());
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'modified':
        return <EditIcon color="primary" />;
      case 'deleted':
        return <DeleteIcon color="error" />;
      case 'new':
        return <AddIcon color="success" />;
      default:
        return <EditIcon />;
    }
  };

  const groupFilesByType = () => {
    const groups = {
      new: [],
      modified: [],
      deleted: []
    };
    
    fileChanges.forEach(change => {
      if (groups[change.type]) {
        groups[change.type].push(change);
      }
    });
    
    return groups;
  };

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ flexGrow: 1, height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <AppBar position="static" elevation={0}>
          <Toolbar>
            <SecurityIcon sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Secure Workspace
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body1" sx={{ mr: 2 }}>
                Secure Mode
              </Typography>
              {loading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                <Switch
                  checked={secureMode}
                  onChange={handleSecureModeToggle}
                  color="secondary"
                />
              )}
            </Box>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
          <Paper elevation={3} sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              File Changes
            </Typography>
            <List>
              {fileChanges.map((change, index) => (
                <ListItem
                  key={index}
                  secondaryAction={
                    <IconButton edge="end" aria-label="save">
                      <SaveIcon />
                    </IconButton>
                  }
                >
                  <ListItemIcon>
                    {getFileIcon(change.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={change.path}
                    secondary={`${change.type} - ${new Date(change.timestamp).toLocaleString()}`}
                  />
                </ListItem>
              ))}
              {fileChanges.length === 0 && (
                <ListItem>
                  <ListItemText
                    primary="No file changes detected"
                    secondary="Changes will appear here when files are modified"
                  />
                </ListItem>
              )}
            </List>
          </Paper>
        </Container>

        <Dialog
          open={showFileDialog}
          onClose={handleCancel}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>Select Files to Preserve</DialogTitle>
          <DialogContent>
            {Object.entries(groupFilesByType()).map(([type, files]) => (
              files.length > 0 && (
                <Box key={type} sx={{ mb: 2 }}>
                  <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                    {type.charAt(0).toUpperCase() + type.slice(1)} Files
                  </Typography>
                  <FormGroup>
                    {files.map((file, index) => (
                      <FormControlLabel
                        key={index}
                        control={
                          <Checkbox
                            checked={selectedFiles.has(file.path)}
                            onChange={() => handleFileSelection(file.path)}
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body1">{file.path}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {new Date(file.timestamp).toLocaleString()}
                            </Typography>
                          </Box>
                        }
                      />
                    ))}
                  </FormGroup>
                  <Divider sx={{ mt: 2 }} />
                </Box>
              )
            ))}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCancel}>Cancel</Button>
            <Button onClick={handleSaveSelected} variant="contained" color="primary">
              Save Selected
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </ThemeProvider>
  );
}

const root = createRoot(document.getElementById('root'));
root.render(<App />); 