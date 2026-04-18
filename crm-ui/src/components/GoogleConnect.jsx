import React, { useState, useEffect } from 'react';
import axios from 'axios';

const GoogleConnect = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/v1/google/status/');
        if (response.data && response.data.connected) {
          setIsConnected(true);
        }
      } catch (error) {
        console.error('Error checking Google status:', error);
      } finally {
        setIsLoading(false);
      }
    };
    checkStatus();
  }, []);

  const handleConnect = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/google/auth/');
      if (response.data && response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error('Error connecting to Google:', error);
      alert('Could not start Google Authentication flow.');
    }
  };

  return (
    <div style={{ padding: '16px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb', marginBottom: '20px' }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Google Workspace Integration</h3>
      <p style={{ margin: '0 0 16px 0', fontSize: '14px', color: '#4b5563' }}>
        Connect your Google account to enable sending emails via Gmail and scheduling reminders via Google Calendar directly from the CRM.
      </p>
      
      {isLoading ? (
        <div style={{ fontSize: '14px', color: '#6b7280' }}>Checking connection...</div>
      ) : isConnected ? (
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: '#ecfdf5',
          color: '#065f46',
          border: '1px solid #a7f3d0',
          padding: '8px 16px',
          borderRadius: '6px',
          fontSize: '14px',
          fontWeight: '500',
        }}>
          <svg fill="currentColor" viewBox="0 0 20 20" width="16px" height="16px"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
          Google Account Connected
        </div>
      ) : (
        <button 
          onClick={handleConnect}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            background: '#ffffff',
            color: '#374151',
            border: '1px solid #d1d5db',
            padding: '10px 16px',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
            transition: 'all 0.2s'
          }}
        >
          <svg fill="#4285F4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="18px" height="18px"><path d="M43.6 20H42V20H24v8h11.3C34.7 32.8 30 36 24 36c-7 0-12.7-5.4-13.8-12.2-.1-.5-.2-1.1-.2-1.8s.1-1.3.2-1.8C11.3 13.4 17 8 24 8c3.1 0 5.9 1.1 8 2.9l5.6-5.6C33.9 1.9 29.3 0 24 0 10.7 0 0 10.7 0 24s10.7 24 24 24c8.8 0 16.4-4.8 20.6-11.9.4-.9.8-1.9 1.1-2.9.2-.8.3-1.6.3-2.5 0-.9-.1-1.8-.3-2.7h-2.1z M43.6 20h.3C43.8 20.3 43.7 20.2 43.6 20z"/></svg>
          Connect Google Account
        </button>
      )}
    </div>
  );
};

export default GoogleConnect;
