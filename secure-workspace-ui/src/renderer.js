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
  Divider,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid
} from '@mui/material';
import {
  Security as SecurityIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Save as SaveIcon,
  History as HistoryIcon,
  Timeline as TimelineIcon,
  Close as CloseIcon
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

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index} style={{ height: '100%' }}>
      {value === index && children}
    </div>
  );
}

function App() {
  const [secureMode, setSecureMode] = useState(false);
  const [fileChanges, setFileChanges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showFileDialog, setShowFileDialog] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [sessionHistory, setSessionHistory] = useState([]);
  const [currentTab, setCurrentTab] = useState(0);

  useEffect(() => {
    // Initial load of file changes and session history
    loadFileChanges();
    loadSessionHistory();
    
    // Listen for real-time updates
    ipcRenderer.on('file-changes-updated', (event, changes) => {
      setFileChanges(changes);
    });

    ipcRenderer.on('session-history-updated', (event, history) => {
      setSessionHistory(history);
    });

    return () => {
      ipcRenderer.removeAllListeners('file-changes-updated');
      ipcRenderer.removeAllListeners('session-history-updated');
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

  const loadSessionHistory = async () => {
    try {
      const history = await ipcRenderer.invoke('get-session-history');
      setSessionHistory(history);
    } catch (error) {
      console.error('Failed to load session history:', error);
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
        setCurrentTab(1); // Switch to history tab
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

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
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

  const renderSessionHistory = () => {
    return sessionHistory.map((session, index) => (
      <Card key={index} sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            {session.type === 'start' ? (
              <SecurityIcon color="primary" sx={{ mr: 1 }} />
            ) : (
              <TimelineIcon color="secondary" sx={{ mr: 1 }} />
            )}
            <Typography variant="h6">
              {session.type === 'start' ? 'Session Started' : 'Session Ended'}
            </Typography>
            <Typography variant="caption" sx={{ ml: 2 }}>
              {new Date(session.timestamp).toLocaleString()}
            </Typography>
          </Box>
          
          {session.type === 'end' && (
            <>
              <Typography variant="subtitle1" gutterBottom>
                Preserved Files:
              </Typography>
              <List dense>
                {session.preservedFiles.map((file, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <SaveIcon color="success" />
                    </ListItemIcon>
                    <ListItemText primary={file} />
                  </ListItem>
                ))}
              </List>
              
              <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                Changes:
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(groupFilesByType(session.changes)).map(([type, files]) => (
                  files.length > 0 && (
                    <Grid item xs={12} key={type}>
                      <Typography variant="subtitle2" color="text.secondary">
                        {type.charAt(0).toUpperCase() + type.slice(1)} Files ({files.length})
                      </Typography>
                      <List dense>
                        {files.map((file, idx) => (
                          <ListItem key={idx}>
                            <ListItemIcon>
                              {getFileIcon(file.type)}
                            </ListItemIcon>
                            <ListItemText
                              primary={file.path}
                              secondary={new Date(file.timestamp).toLocaleString()}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Grid>
                  )
                ))}
              </Grid>
            </>
          )}
        </CardContent>
      </Card>
    ));
  };

  const handleClose = () => {
    window.close();
  };

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ flexGrow: 1, height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <AppBar position="static" sx={{ WebkitAppRegion: 'drag' }}>
          <Toolbar>
            <SecurityIcon sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Secure Workspace
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', WebkitAppRegion: 'no-drag' }}>
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
              <IconButton 
                color="inherit" 
                onClick={handleClose}
                sx={{ ml: 2 }}
              >
                <CloseIcon />
              </IconButton>
            </Box>
          </Toolbar>
        </AppBar>

        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={currentTab} onChange={handleTabChange}>
            <Tab icon={<TimelineIcon />} label="Current Session" />
            <Tab icon={<HistoryIcon />} label="Session History" />
          </Tabs>
        </Box>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4, flexGrow: 1, overflow: 'auto' }}>
          <TabPanel value={currentTab} index={0}>
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
          </TabPanel>

          <TabPanel value={currentTab} index={1}>
            <Box sx={{ height: '100%', overflow: 'auto' }}>
              {sessionHistory.length === 0 ? (
                <Paper elevation={3} sx={{ p: 2 }}>
                  <Typography variant="body1" color="text.secondary" align="center">
                    No session history available
                  </Typography>
                </Paper>
              ) : (
                renderSessionHistory()
              )}
            </Box>
          </TabPanel>
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