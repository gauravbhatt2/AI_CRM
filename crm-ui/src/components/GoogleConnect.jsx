import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const GoogleConnect = ({ minimal = false }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  const checkStatus = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/v1/google/status/');
      setIsConnected(response.data && response.data.connected);
    } catch (error) {
      console.error('Error checking Google status:', error);
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
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

  const handleReauthorize = async () => {
    setShowDropdown(false);
    handleConnect();
  };

  const handleRefreshStatus = async () => {
    setShowDropdown(false);
    await checkStatus();
  };

  return (
    <div style={minimal ? { position: 'relative' } : { padding: '16px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb', marginBottom: '20px' }}>
      {!minimal && (
        <>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Google Workspace Integration</h3>
          <p style={{ margin: '0 0 16px 0', fontSize: '14px', color: '#4b5563' }}>
            Connect your Google account to enable sending emails via Gmail and scheduling reminders via Google Calendar directly from the CRM.
          </p>
        </>
      )}

      {isLoading ? (
        <div style={{ fontSize: '14px', color: '#6b7280' }}>Checking connection...</div>
      ) : isConnected ? (
        <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block' }}>
          {/* Connected badge — clickable */}
          <button
            onClick={() => setShowDropdown((v) => !v)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: '#ecfdf5',
              color: '#065f46',
              border: '1px solid #a7f3d0',
              padding: '8px 14px',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'background 0.15s',
            }}
          >
            <svg fill="currentColor" viewBox="0 0 20 20" width="16px" height="16px">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Google Account Connected
            <svg fill="currentColor" viewBox="0 0 20 20" width="12px" height="12px" style={{ opacity: 0.6 }}>
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>

          {/* Status dropdown */}
          {showDropdown && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: 0,
              background: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '10px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.15)',
              minWidth: '240px',
              zIndex: 1000,
              overflow: 'hidden',
            }}>
              {/* Status header */}
              <div style={{ padding: '14px 16px', borderBottom: '1px solid #f3f4f6' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ width: '8px', height: '8px', background: '#10b981', borderRadius: '50%', display: 'inline-block' }} />
                  <span style={{ fontSize: '13px', fontWeight: '600', color: '#111827' }}>OAuth Status: Active</span>
                </div>
                <p style={{ margin: 0, fontSize: '12px', color: '#6b7280' }}>
                  This account is authorized as an OAuth test user. Gmail &amp; Calendar access is active.
                </p>
              </div>

              {/* Actions */}
              <div style={{ padding: '8px' }}>
                <button
                  onClick={handleRefreshStatus}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    width: '100%', padding: '8px 10px', background: 'transparent',
                    border: 'none', borderRadius: '6px', fontSize: '13px',
                    color: '#374151', cursor: 'pointer', textAlign: 'left',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f9fafb'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  🔄 Refresh Status
                </button>
                <button
                  onClick={handleReauthorize}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    width: '100%', padding: '8px 10px', background: 'transparent',
                    border: 'none', borderRadius: '6px', fontSize: '13px',
                    color: '#374151', cursor: 'pointer', textAlign: 'left',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f9fafb'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  🔑 Re-authorize Account
                </button>
              </div>
            </div>
          )}
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
          <svg fill="#4285F4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="18px" height="18px"><path d="M43.6 20H42V20H24v8h11.3C34.7 32.8 30 36 24 36c-7 0-12.7-5.4-13.8-12.2-.1-.5-.2-1.1-.2-1.8s.1-1.3.2-1.8C11.3 13.4 17 8 24 8c3.1 0 5.9 1.1 8 2.9l5.6-5.6C33.9 1.9 29.3 0 24 0 10.7 0 0 10.7 0 24s10.7 24 24 24c8.8 0 16.4-4.8 20.6-11.9.4-.9.8-1.9 1.1-2.9.2-.8.3-1.6.3-2.5 0-.9-.1-1.8-.3-2.7h-2.1z"/></svg>
          Connect Google Account
        </button>
      )}
    </div>
  );
};

export default GoogleConnect;
