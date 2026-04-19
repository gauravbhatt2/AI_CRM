import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion as Motion } from 'framer-motion';

const Sidebar = ({ onChatOpen }) => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: 'dashboard' },
    { name: 'AI Intelligence', path: '/intelligence', icon: 'psychology' },
    { name: 'Timeline', path: '/timeline', icon: 'schedule' },
    { name: 'Upload', path: '/upload', icon: 'upload' },
    { name: 'Analytics', path: '/analytics', icon: 'insights' },
    { name: 'CRM Records', path: '/records', icon: 'storage' },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen flex flex-col justify-between py-8 w-64 border-none bg-background dark:bg-[#1a1c1e] shadow-[12px_0_32px_-4px_rgba(32,27,20,0.04)] z-50">
      <div>
        <div className="px-8 mb-10">
          <h1 className="text-xl font-black text-primary dark:text-[#ede1d5] tracking-tighter uppercase font-headline">
            Editorial Intelligence
          </h1>
          <p className="font-headline font-bold tracking-tight uppercase text-[10px] opacity-50">
            AI CRM Core
          </p>
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `px-6 py-3 flex items-center gap-3 transition-all duration-300 ${
                  isActive
                    ? 'text-primary dark:text-white font-bold bg-[#ede1d5] dark:bg-primary rounded-r-full mr-4 border-l-4 border-secondary scale-[0.98]'
                    : 'text-[#424b54]/70 dark:text-stone-400 font-medium hover:text-primary hover:bg-[#ede1d5]/30'
                }`
              }
            >
              <span className="material-symbols-outlined text-xl">{item.icon}</span>
              <span className="font-headline font-bold tracking-tight uppercase text-xs">
                {item.name}
              </span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="flex flex-col gap-1">
        <div className="px-6 mb-6">
          <Motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.95 }}
            onClick={onChatOpen}
            className="w-full py-3 px-4 bg-gradient-to-br from-primary to-primary-container text-on-primary rounded-xl font-headline font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-primary/20 transition-all"
          >
            <span className="material-symbols-outlined text-sm">auto_awesome</span>
            AI CHATBOT
          </Motion.button>
        </div>
        <NavLink
          to="/settings"
          className="text-[#424b54]/70 dark:text-stone-400 font-medium px-6 py-2 hover:text-primary hover:bg-[#ede1d5]/30 flex items-center gap-3 transition-all"
        >
          <span className="material-symbols-outlined text-xl">settings</span>
          <span className="font-headline font-bold tracking-tight uppercase text-xs">Settings</span>
        </NavLink>
        <NavLink
          to="/support"
          className="text-[#424b54]/70 dark:text-stone-400 font-medium px-6 py-2 hover:text-primary hover:bg-[#ede1d5]/30 flex items-center gap-3 transition-all"
        >
          <span className="material-symbols-outlined text-xl">contact_support</span>
          <span className="font-headline font-bold tracking-tight uppercase text-xs">Support</span>
        </NavLink>
      </div>
    </aside>
  );
};

export default Sidebar;
