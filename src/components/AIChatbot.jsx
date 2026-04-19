import React from 'react';
import { motion as Motion, AnimatePresence } from 'framer-motion';

const AIChatbot = ({ isOpen, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <Motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[60] bg-primary/20 backdrop-blur-sm shadow-2xl"
          />
          
          {/* Panel */}
          <Motion.div 
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 bottom-0 w-[450px] bg-background shadow-[24px_0_64px_-12px_rgba(32,27,20,0.15)] flex flex-col border-r border-outline-variant/10 z-[70]"
          >
            {/* Header */}
            <div className="h-20 px-8 flex items-center justify-between bg-surface-container-low border-b border-outline-variant/10">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white shadow-lg">
                  <span className="material-symbols-outlined text-xl">smart_toy</span>
                </div>
                <div>
                  <h3 className="text-sm font-bold font-headline text-primary uppercase tracking-tight">Editorial AI</h3>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
                    <span className="text-[10px] font-bold text-secondary uppercase tracking-widest">Active Analysis</span>
                  </div>
                </div>
              </div>
              <button 
                onClick={onClose}
                className="hover:bg-surface-container-highest rounded-full p-2 transition-colors"
              >
                <span className="material-symbols-outlined text-primary">close</span>
              </button>
            </div>

            {/* Chat Content */}
            <div className="flex-1 overflow-y-auto p-8 flex flex-col gap-6 custom-scrollbar">
              {/* User Message */}
              <div className="flex flex-col items-end">
                <div className="bg-[#C5BAAF] text-primary p-4 rounded-2xl rounded-tr-none max-w-[85%] shadow-sm">
                  <p className="text-sm leading-relaxed">Could you analyze the revenue impact if the Genesis deal slips to Q1?</p>
                </div>
                <span className="text-[10px] font-bold text-secondary/40 uppercase mt-2 px-1">10:42 AM</span>
              </div>

              {/* AI Message */}
              <div className="flex flex-col items-start">
                <div className="bg-primary-container text-white p-5 rounded-2xl rounded-tl-none max-w-[90%] shadow-lg">
                  <p className="text-sm leading-relaxed">
                    If <span className="font-bold text-secondary-container">Project Genesis ($1.2M)</span> moves to Q1, the current quarter will likely finish at <span className="font-bold text-secondary-container">92% of target</span>.
                  </p>
                  <div className="mt-4 p-3 bg-white/5 rounded-lg border border-white/10 flex flex-col gap-2">
                    <p className="text-[11px] font-medium opacity-80 uppercase tracking-wider">Suggested Mitigation:</p>
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-sm text-secondary-container">bolt</span>
                      <p className="text-[12px]">Expedite 'Project Orion' signatures to recover 40% of the gap.</p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-2 px-1">
                  <span className="text-[10px] font-bold text-secondary/40 uppercase">AI ANALYST</span>
                  <div className="flex gap-1">
                    <button className="material-symbols-outlined text-xs text-secondary/40 hover:text-secondary">thumb_up</button>
                    <button className="material-symbols-outlined text-xs text-secondary/40 hover:text-secondary">content_copy</button>
                  </div>
                </div>
              </div>

              {/* AI Typing Indicator */}
              <div className="flex items-center gap-2 px-1">
                <div className="bg-surface-container-highest px-4 py-3 rounded-full flex gap-1.5 items-center">
                  <Motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1 }} className="w-1.5 h-1.5 rounded-full bg-secondary"></Motion.div>
                  <Motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} className="w-1.5 h-1.5 rounded-full bg-secondary"></Motion.div>
                  <Motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} className="w-1.5 h-1.5 rounded-full bg-secondary"></Motion.div>
                </div>
                <span className="text-[10px] font-bold text-secondary/40 uppercase tracking-widest">Processing Data...</span>
              </div>
            </div>

            {/* Chat Footer */}
            <div className="p-6 bg-surface-container-low border-t border-outline-variant/10">
              {/* Suggested Prompts */}
              <div className="flex gap-2 mb-6 overflow-x-auto pb-2 no-scrollbar">
                {['Show high-risk interactions', 'What deals need follow-up?', 'Forecast Q1'].map((prompt, i) => (
                  <button 
                    key={i}
                    className="whitespace-nowrap px-4 py-2 bg-surface-container-highest rounded-full text-[10px] font-bold text-primary uppercase tracking-widest border border-outline-variant/20 hover:bg-surface-variant transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              {/* Input Field */}
              <div className="relative group">
                <input 
                  className="w-full bg-surface-container-highest border-none rounded-2xl py-4 pl-6 pr-14 text-sm focus:ring-2 focus:ring-secondary/20 transition-all font-body text-primary placeholder-primary/40" 
                  placeholder="Ask intelligence..." 
                  type="text"
                />
                <button className="absolute right-2 top-2 bottom-2 w-10 bg-primary text-white rounded-xl flex items-center justify-center shadow-md active:scale-90 transition-transform">
                  <span className="material-symbols-outlined text-lg">send</span>
                </button>
              </div>
              <p className="text-center text-[9px] text-secondary/40 mt-4 font-medium uppercase tracking-[0.2em]">Powered by Editorial AI Core 4.0</p>
            </div>
          </Motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default AIChatbot;
