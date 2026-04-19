import React from 'react';
import { motion as Motion } from 'framer-motion';

const TopBar = () => {
  return (
    <header className="fixed top-0 right-0 left-64 flex justify-between items-center px-12 z-40 h-20 bg-background/80 backdrop-blur-xl">
      <div className="flex items-center flex-1">
        <div className="relative w-96 flex items-center bg-surface-container-high rounded-full px-4 py-2 focus-within:ring-2 focus-within:ring-secondary/20 transition-all">
          <span className="material-symbols-outlined text-on-surface-variant mr-2">search</span>
          <input
            className="bg-transparent border-none focus:ring-0 text-sm font-medium w-full text-on-surface placeholder-on-surface-variant/50"
            placeholder="Search editorial archives..."
            type="text"
          />
        </div>
      </div>
      
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Motion.button 
            whileHover={{ backgroundColor: 'rgba(0,0,0,0.05)' }}
            className="rounded-full p-2 transition-colors relative"
          >
            <span className="material-symbols-outlined text-primary">notifications</span>
            <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full border border-background"></span>
          </Motion.button>
          <Motion.button 
            whileHover={{ backgroundColor: 'rgba(0,0,0,0.05)' }}
            className="rounded-full p-2 transition-colors"
          >
            <span className="material-symbols-outlined text-primary">apps</span>
          </Motion.button>
        </div>

        <div className="flex items-center gap-3 pl-4 border-l border-outline-variant/20">
          <div className="text-right">
            <p className="text-sm font-bold font-headline text-primary">Marcus Sterling</p>
            <p className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">
              Chief Revenue Officer
            </p>
          </div>
          <div className="relative group cursor-pointer">
            <img
              alt="Chief Revenue Officer"
              className="w-10 h-10 rounded-full object-cover border-2 border-surface-container-highest shadow-sm group-hover:border-secondary transition-all"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBtQTWHm-v4WHatuMZBHg0jFI0BiOJxD04RvFvhLUVLVoKhKvjIoO1wmU1WJqrDqazw-RakV1EaU1J-RAQ4BA4Sx19n195JVG6NjRR-bdWKqr9Ci7t_Kl5s-w-vwpPE4zp-YBo9H5uv5oIhZlgIyL6udNaonECCov_bx_oSYaT6XzIH3uNazFdMXFeYB7JMbjZZe5d7MEBELOG6rSs2v2BRIQtqsIH2yxxuCI96qsw2lol-jJVmRuGxP59wmbVyvVpou3KUJNfWWLc"
            />
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-success rounded-full border-2 border-background"></div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
