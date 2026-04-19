import React from 'react';
import { motion as Motion } from 'framer-motion';

const ProcessingStage = ({ icon, title, status, progress, active, completed }) => (
  <div className={`flex items-center gap-6 ${!active && !completed ? 'opacity-40' : ''}`}>
    <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
      completed ? 'bg-secondary-container text-secondary' : 'bg-surface-container text-primary'
    } ${active ? 'animate-pulse' : ''}`}>
      <span className="material-symbols-outlined text-xl" style={{ fontVariationSettings: completed ? "'FILL' 1" : "'FILL' 0" }}>
        {completed ? 'check_circle' : icon}
      </span>
    </div>
    <div className="flex-grow">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-bold text-primary">{title}</span>
        <span className={`text-[10px] font-bold uppercase tracking-wider ${completed ? 'text-secondary' : 'text-on-surface-variant'}`}>
          {status}
        </span>
      </div>
      <div className="h-1 bg-surface-container-high rounded-full overflow-hidden">
        <Motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          className={`h-full ${completed ? 'bg-secondary' : 'bg-primary'}`}
        />
      </div>
    </div>
  </div>
);

const Upload = () => {
  return (
    <div className="max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-1">
          <span className="text-secondary font-bold tracking-widest text-[10px] uppercase">Data Ingression</span>
          <h1 className="text-4xl md:text-5xl font-extrabold text-primary tracking-tighter leading-none">Upload Intelligence</h1>
          <p className="text-on-surface-variant max-w-md text-sm mt-4 font-medium leading-relaxed">
            Inject sales transcripts, call recordings, or CRM exports to let the core engine extract strategic intent and risk markers.
          </p>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[10px] font-bold text-on-surface-variant uppercase mb-1">Weekly Limit</span>
          <div className="w-48 h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
            <div className="h-full bg-secondary w-[65%]"></div>
          </div>
          <span className="text-[10px] mt-1 font-medium">13 / 20 uploads remaining</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column */}
        <div className="lg:col-span-7 space-y-8">
          {/* Drag & Drop Zone */}
          <Motion.div 
            whileHover={{ scale: 1.01 }}
            className="relative group cursor-pointer"
          >
            <div className="absolute -inset-0.5 bg-gradient-to-r from-secondary/20 to-primary/10 rounded-xl blur opacity-30 group-hover:opacity-50 transition duration-1000"></div>
            <div className="relative bg-surface-container-low rounded-xl p-16 flex flex-col items-center justify-center text-center border-2 border-dashed border-outline-variant/30 group-hover:border-secondary/40 transition-all duration-500">
              <div className="w-20 h-20 bg-surface-container-highest rounded-full flex items-center justify-center mb-6 shadow-sm group-hover:scale-110 transition-transform duration-500">
                <span className="material-symbols-outlined text-4xl text-secondary">cloud_upload</span>
              </div>
              <h3 className="text-xl font-bold text-primary mb-2">Drop your intelligence here</h3>
              <p className="text-on-surface-variant text-sm mb-8 font-medium">MP3, WAV, PDF or CSV files (Up to 500MB)</p>
              <button className="bg-gradient-to-r from-primary to-primary-container text-white px-8 py-3 rounded-full text-sm font-bold shadow-lg shadow-primary/10 hover:shadow-primary/20 transition-all">
                Select from Computer
              </button>
            </div>
          </Motion.div>

          {/* Pipeline */}
          <div className="bg-surface-container-lowest rounded-xl p-8 space-y-6 shadow-sm">
            <h4 className="text-xs font-bold text-secondary tracking-widest uppercase mb-4">Core Processing Pipeline</h4>
            <ProcessingStage icon="cloud_upload" title="Uploading Stream" status="Completed" progress={100} completed={true} />
            <ProcessingStage icon="psychology" title="Linguistic Pattern Recognition" status="84% Analyzed" progress={84} active={true} />
            <ProcessingStage icon="verified" title="Strategic Insight Finalization" status="Waiting" progress={0} />
          </div>
        </div>

        {/* Right Column */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-primary text-white rounded-xl p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-10">
              <span className="material-symbols-outlined text-9xl">auto_awesome</span>
            </div>
            <div className="relative z-10">
              <span className="text-[10px] font-bold text-secondary tracking-[0.2em] uppercase">Intelligence Live-Feed</span>
              <h3 className="text-2xl font-bold mt-2 mb-6">Emerging Insights</h3>
              <div className="space-y-6">
                <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border-l-4 border-secondary">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-secondary text-sm">warning</span>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-secondary">Risk Marker Detected</span>
                  </div>
                  <p className="text-xs leading-relaxed text-white/80 italic">
                    "...budget approval timeframe seems uncertain given the current quarter constraints..."
                  </p>
                  <div className="mt-3 flex justify-between items-center">
                    <span className="text-[10px] font-bold text-white/40">Timestamp: 04:12</span>
                    <span className="bg-secondary text-on-secondary px-2 py-0.5 rounded text-[8px] font-black uppercase">High Priority</span>
                  </div>
                </div>

                <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border-l-4 border-white/20">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-white/60 text-sm">trending_up</span>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white">Intent Analysis</span>
                  </div>
                  <p className="text-xs leading-relaxed text-white/80 italic">
                    "Buyer shows 82% affinity toward 'Expansion' feature set over 'Security' core."
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-surface-container-high rounded-xl p-6">
              <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest block mb-2">Sentiment</span>
              <div className="text-3xl font-black text-primary tracking-tighter">Neutral</div>
              <div className="mt-2 flex items-center gap-1 text-[10px] text-secondary font-bold">
                <span className="material-symbols-outlined text-xs">arrow_drop_up</span> Shift +12%
              </div>
            </div>
            <div className="bg-surface-container-high rounded-xl p-6">
              <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest block mb-2">Confidence</span>
              <div className="text-3xl font-black text-primary tracking-tighter">94%</div>
              <div className="mt-2 flex items-center gap-1 text-[10px] text-primary font-bold">
                <span className="material-symbols-outlined text-xs">done_all</span> Core Verified
              </div>
            </div>
          </div>

          <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h4 className="text-xs font-bold text-secondary tracking-widest uppercase">Transcript Snippet</h4>
              <span className="material-symbols-outlined text-on-surface-variant cursor-pointer hover:text-primary">open_in_full</span>
            </div>
            <div className="space-y-4 font-body text-xs text-on-surface-variant leading-loose">
              <p><strong className="text-primary uppercase tracking-tighter text-[10px]">Sales:</strong> Thanks for joining today. I wanted to touch base on the proposed architecture for your editorial platform.</p>
              <p><strong className="text-secondary uppercase tracking-tighter text-[10px]">Lead:</strong> We've seen the deck. My main concern is how the AI intent engine integrates with our existing storage records.</p>
              <p className="blur-[1px] select-none italic text-opacity-50">... processing remaining text and identifying key decision makers ...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
