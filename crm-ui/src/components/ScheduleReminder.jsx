import React, { useState } from 'react';
import axios from 'axios';

const ScheduleReminder = ({ contactId, dealId, defaultEmail = "", onClose }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [attendees, setAttendees] = useState(defaultEmail);
  const [status, setStatus] = useState(null);

  const handleSchedule = async (e) => {
    e.preventDefault();
    setStatus('scheduling');
    try {
      const attendeeList = attendees.split(',').map(email => email.trim()).filter(Boolean);
      await axios.post('http://localhost:8000/api/v1/google/calendar/schedule', {
        title,
        description,
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
        attendees: attendeeList,
        contact_id: contactId,
        deal_id: dealId
      });
      setStatus('success');
      setTitle('');
      setDescription('');
      setStartTime('');
      setEndTime('');
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  return (
    <div style={{ padding: '24px', background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', marginBottom: '20px', width: '100%', maxWidth: '600px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: '0', fontSize: '20px', fontWeight: '600', color: '#111827' }}>Schedule Meeting</h3>
        {onClose && (
          <button
            onClick={onClose}
            type="button"
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#6b7280', fontSize: '18px' }}
          >
            ✕
          </button>
        )}
      </div>
      
      {status === 'success' && (
        <div style={{ padding: '12px', background: '#def7ec', color: '#03543f', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>
          Event scheduled successfully and logged to CRM!
        </div>
      )}
      {status === 'error' && (
        <div style={{ padding: '12px', background: '#fde8e8', color: '#9b1c1c', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>
          Failed to schedule event. Please ensure you have connected your Google account.
        </div>
      )}

      <form onSubmit={handleSchedule} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Event Title</label>
          <input 
            type="text" 
            required 
            value={title} 
            onChange={(e) => setTitle(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Start Time</label>
            <input 
              type="datetime-local" 
              required 
              value={startTime} 
              onChange={(e) => setStartTime(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>End Time</label>
            <input 
              type="datetime-local" 
              required 
              value={endTime} 
              onChange={(e) => setEndTime(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
            />
          </div>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Attendees (comma-separated emails)</label>
          <input 
            type="text" 
            value={attendees} 
            onChange={(e) => setAttendees(e.target.value)}
            placeholder="guest@example.com, another@example.com"
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Description</label>
          <textarea 
            rows={3}
            value={description} 
            onChange={(e) => setDescription(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          />
        </div>
        <button 
          type="submit" 
          disabled={status === 'scheduling'}
          style={{
            background: '#10b981',
            color: 'white',
            border: 'none',
            padding: '10px 16px',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: status === 'scheduling' ? 'not-allowed' : 'pointer',
            opacity: status === 'scheduling' ? 0.7 : 1,
            marginTop: '8px'
          }}
        >
          {status === 'scheduling' ? 'Scheduling...' : 'Schedule Event'}
        </button>
      </form>
    </div>
  );
};

export default ScheduleReminder;
