# Secure Workspace UI

A modern Electron-based UI application for managing your secure workspace.

## Features

- Toggle secure mode on/off with a beautiful switch
- Real-time file change monitoring
- Interactive file change list with icons
- Save modified files functionality
- Modern Material-UI design
- Smooth animations and transitions

## Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)
- Python 3.x (for the backend secure workspace functionality)

## Installation

1. Install dependencies:
```bash
npm install
```

2. Make sure the Python backend files (`secure_workspace.py`, `start_session.py`, and `stop_session.py`) are in the correct location relative to the UI application.

## Development

To run the application in development mode:

```bash
npm run dev
```

This will start the application with DevTools enabled.

## Building

To build the application for production:

```bash
npm run build
```

The built application will be available in the `dist` directory.

## Project Structure

- `src/main.js` - Main Electron process
- `src/renderer.js` - React application entry point
- `src/index.html` - HTML template
- `src/styles.css` - Custom styles

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request 