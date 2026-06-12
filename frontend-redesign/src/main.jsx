import React from 'react';
import ReactDOM from 'react-dom/client';
import '../redesign.css';
import { ApiProvider } from './api.jsx';
import { AppShell } from './app.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <ApiProvider>
    <AppShell />
  </ApiProvider>
);
