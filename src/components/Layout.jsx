import React, { useState } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import AIChatbot from './AIChatbot';

const Layout = ({ children }) => {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background text-on-surface">
      <Sidebar onChatOpen={() => setIsChatOpen(true)} />
      <TopBar />
      <AIChatbot isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
      <main className="ml-64 pt-20 px-12 pb-12 transition-all">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
