import React, { useState } from 'react';
import axios from 'axios';

const EmailComposer = ({ contactId, dealId, defaultEmail = "" }) => {
  const [to, setTo] = useState(defaultEmail);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [status, setStatus] = useState(null);

  const handleSend = async (e) => {
    e.preventDefault();
    setStatus('sending');
    try {
      await axios.post('http://localhost:8000/api/v1/google/gmail/send', {
        to,
        subject,
        body,
        contact_id: contactId,
        deal_id: dealId
      });
      setStatus('success');
      setSubject('');
      setBody('');
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  return (
    <div style={{ padding: '16px', background: '#ffffff', borderRadius: '8px', border: '1px solid #e5e7eb', marginBottom: '20px' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Send Email via Gmail</h3>
      
      {status === 'success' && (
        <div style={{ padding: '12px', background: '#def7ec', color: '#03543f', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>
          Email sent successfully and logged to CRM!
        </div>
      )}
      {status === 'error' && (
        <div style={{ padding: '12px', background: '#fde8e8', color: '#9b1c1c', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>
          Failed to send email. Please ensure you have connected your Google account.
        </div>
      )}

      <form onSubmit={handleSend} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>To</label>
          <input 
            type="email" 
            required 
            value={to} 
            onChange={(e) => setTo(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Subject</label>
          <input 
            type="text" 
            required 
            value={subject} 
            onChange={(e) => setSubject(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Message Body (HTML supported)</label>
          <textarea 
            required 
            rows={5}
            value={body} 
            onChange={(e) => setBody(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          />
        </div>
        <button 
          type="submit" 
          disabled={status === 'sending'}
          style={{
            background: '#2563eb',
            color: 'white',
            border: 'none',
            padding: '10px 16px',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: status === 'sending' ? 'not-allowed' : 'pointer',
            opacity: status === 'sending' ? 0.7 : 1,
            marginTop: '8px'
          }}
        >
          {status === 'sending' ? 'Sending...' : 'Send Email'}
        </button>
      </form>
    </div>
  );
};

export default EmailComposer;
