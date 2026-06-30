import React, { useState, useEffect } from 'react';
import ChatConsole from './components/ChatConsole';
import SidePanel from './components/SidePanel';
import * as api from './api';
import './index.css';

function App() {
  // --- New Configuration State (Step A) ---
  const [repoName, setRepoName] = useState('');
  const [statusMessage, setStatusMessage] = useState(null);

  // --- Existing / Refactored State ---
  const [projectState, setProjectState] = useState(null);

  // Load configuration on mount (Step A)
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await api.getProjectConfig();
      if (data && data.state && data.state.repo_name) {
        setRepoName(data.state.repo_name);
      }
    } catch (err) {
      console.error(err);
      setStatusMessage({ type: 'error', text: 'Failed to load config' });
    }
  };

  // Wire the Save Action (Step C)
  const handleSaveConfig = async () => {
    setStatusMessage(null);
    try {
      const response = await api.updateProjectConfig(repoName);
      if (response.error) {
        setStatusMessage({ type: 'error', text: response.error });
      } else {
        setStatusMessage({ type: 'success', text: 'Configuration saved!' });
        // Clear message after 3 seconds
        setTimeout(() => setStatusMessage(null), 3000);
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: 'Error saving configuration.' });
    }
  };

  // Handle state transitions via the API Gateway
  const handleAction = async (action) => {
    try {
      const response = await api.triggerChatAction(action);
      if (!response.error) {
        setProjectState(response);
      } else {
        setStatusMessage({ type: 'error', text: response.error });
      }
    } catch (err) {
      console.error(err);
      setStatusMessage({ type: 'error', text: `Failed to execute ${action}` });
    }
  };

  const handleFinishSharing = () => handleAction('finish-sharing');
  const handleApproveGoals = () => handleAction('approve-goals');
  const handleRejectGoals = () => handleAction('reject-goals');
  const handleUnlockRequirements = () => handleAction('unlock-requirements');

  return (
    <div className="app">
      <header className="header">
        <div className="header__brand">
          <div className="header__icon">✧</div>
          <h1 className="header__title">AI Project Manager</h1>
        </div>
        
        {/* Step B: Build the Settings Component */}
        <div className="header__settings" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', color: '#9CA3AF', fontWeight: '500' }}>TARGET REPO:</span>
          <input 
            type="text" 
            value={repoName} 
            onChange={(e) => setRepoName(e.target.value)} 
            placeholder="owner/repo"
            style={{ 
              padding: '6px 12px', 
              borderRadius: '6px', 
              border: '1px solid #374151', 
              background: '#111827', 
              color: '#F3F4F6',
              outline: 'none',
              width: '200px'
            }}
          />
          <button 
            onClick={handleSaveConfig}
            style={{ 
              padding: '6px 16px', 
              borderRadius: '6px', 
              background: '#2563EB', 
              border: 'none', 
              color: 'white', 
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
          >
            Save
          </button>
          
          {/* Temporary Status Feedback */}
          {statusMessage && (
            <span style={{ 
              fontSize: '13px', 
              color: statusMessage.type === 'success' ? '#10B981' : '#EF4444',
              fontWeight: '500'
            }}>
              {statusMessage.text}
            </span>
          )}
        </div>

        <div className="header__status">
          <div className="header__status-dot"></div>
          System Online
        </div>
      </header>

      <main className="main" style={{ display: 'flex', flexDirection: 'row', width: '100%', overflow: 'hidden' }}>
        {/* Chat Interface (Swapped to 65% width) */}
        <div style={{ flex: '0 0 65%', height: '100%', borderRight: '1px solid #374151', display: 'flex', flexDirection: 'column' }}>
          <ChatConsole onStateUpdate={setProjectState} />
        </div>
        
        {/* Kanban Board / Side Panel (Swapped to 35% width) */}
        <div style={{ flex: '0 0 35%', height: '100%', backgroundColor: '#0F172A', display: 'flex', flexDirection: 'column' }}>
          {/* Inject style to override the old 380px fixed width on the SidePanel */}
          <style>{`.side-panel { width: 100% !important; max-width: 100% !important; border-left: none !important; }`}</style>
          <SidePanel
            projectState={projectState}
            onApproveGoals={handleApproveGoals}
            onRejectGoals={handleRejectGoals}
            onUnlockRequirements={handleUnlockRequirements}
            onFinishSharing={handleFinishSharing}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
