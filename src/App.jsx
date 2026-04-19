import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Timeline from './pages/Timeline';
import Upload from './pages/Upload';
import { AIIntelligence, Analytics, CRMRecords } from './pages/OtherPages';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout><Dashboard /></Layout>} />
        <Route path="/intelligence" element={<AIIntelligence />} />
        <Route path="/timeline" element={<Layout><Timeline /></Layout>} />
        <Route path="/upload" element={<Layout><Upload /></Layout>} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/records" element={<CRMRecords />} />
        {/* Placeholder for settings/support */}
        <Route path="/settings" element={<Layout><div className="py-10 text-center"><h2 className="text-4xl font-extrabold text-primary font-headline tracking-tighter mb-4">Settings</h2><p className="text-on-surface-variant font-body">Account and application preferences.</p></div></Layout>} />
        <Route path="/support" element={<Layout><div className="py-10 text-center"><h2 className="text-4xl font-extrabold text-primary font-headline tracking-tighter mb-4">Support</h2><p className="text-on-surface-variant font-body">Contact technical assistance.</p></div></Layout>} />
      </Routes>
    </Router>
  );
}

export default App;
