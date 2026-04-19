import React from 'react';
import { motion as Motion } from 'framer-motion';

const TimelineEntry = ({ type, date, title, content, risk, riskColor, accentColor, children }) => (
  <Motion.div 
    initial={{ opacity: 0, x: -20 }}
    whileInView={{ opacity: 1, x: 0 }}
    viewport={{ once: true }}
    className="relative pl-16 group mb-12"
  >
    {/* Marker */}
    <div className="absolute left-0 top-0 w-16 h-16 flex items-center justify-center">
      <div className={`w-4 h-4 rounded-full ${accentColor} ring-4 ring-opacity-20 z-10 transition-transform group-hover:scale-125`}></div>
    </div>
    
    <div className={`bg-surface-container-low rounded-xl p-8 shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)] border-l-4 ${accentColor} flex flex-col md:flex-row gap-8 transition-all hover:shadow-lg`}>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className={`text-[10px] font-headline font-extrabold tracking-widest uppercase px-2 py-1 rounded ${accentColor.replace('bg-', 'text-').replace('border-', 'text-')} bg-opacity-10`}>
              {type}
            </span>
            <span className="text-xs text-on-surface-variant font-medium">{date}</span>
          </div>
          {risk && (
            <span className={`flex items-center gap-1 text-[10px] font-bold ${riskColor} px-2 py-1 rounded-full bg-opacity-10`}>
              <span className="material-symbols-outlined text-sm">warning</span> {risk}
            </span>
          )}
        </div>
        <h3 className="font-headline text-xl font-bold text-primary mb-3">{title}</h3>
        {content && (
          <div className="bg-surface-container-lowest p-5 rounded-lg border-l-2 border-secondary italic text-sm text-on-surface-variant leading-relaxed">
            "{content}"
          </div>
        )}
      </div>
      <div className="md:w-64 flex flex-col gap-4">
        {children}
      </div>
    </div>
  </Motion.div>
);

const Timeline = () => {
  return (
    <div className="max-w-5xl mx-auto py-10">
      {/* Page Header */}
      <div className="mb-12 flex justify-between items-end">
        <div>
          <h2 className="font-headline text-4xl font-extrabold text-primary tracking-tighter mb-2">Deal Velocity Timeline</h2>
          <p className="text-on-surface-variant font-body text-sm max-w-lg leading-relaxed">
            An editorial reconstruction of interaction history for <span className="font-bold text-primary">Global Logistics Corp</span>. Prioritizing AI-detected signals and risk vectors.
          </p>
        </div>
        <div className="flex gap-3">
          <button className="bg-surface-container-lowest text-primary px-5 py-2.5 rounded-full text-sm font-semibold shadow-sm flex items-center gap-2 hover:bg-surface-variant transition-colors">
            <span className="material-symbols-outlined text-lg">filter_list</span>
            All Events
          </button>
          <Motion.button 
            whileHover={{ scale: 1.05 }}
            className="bg-secondary text-white px-5 py-2.5 rounded-full text-sm font-semibold flex items-center gap-2 shadow-lg shadow-secondary/20"
          >
            <span className="material-symbols-outlined text-lg">auto_awesome</span>
            AI Summary
          </Motion.button>
        </div>
      </div>

      {/* Vertical Timeline */}
      <div className="relative">
        <div className="absolute left-[31px] top-0 bottom-0 w-[2px] bg-gradient-to-b from-secondary/30 via-outline-variant/20 to-transparent"></div>
        
        <div className="space-y-4">
          <TimelineEntry 
            type="AI-DETECTED MOMENT"
            date="Oct 24, 2:15 PM"
            title="Pricing Friction Detected in Quarterly Review"
            content="honestly, the new tiered pricing model feels like a significant jump compared to the previous MSA. We need to see more tangible ROI before committing to this expansion."
            risk="HIGH RISK"
            riskColor="text-error"
            accentColor="bg-error border-error"
          >
            <div className="p-4 bg-[#fef2e6] rounded-lg">
              <p className="text-[10px] font-bold text-secondary uppercase tracking-wider mb-2">Intent Analysis</p>
              <p className="text-xs font-semibold text-primary">Postponement / Re-negotiation Sentiment</p>
            </div>
            <button className="w-full bg-primary text-on-primary py-2.5 rounded-lg text-xs font-bold hover:bg-primary-container transition-colors">
              Generate Response
            </button>
          </TimelineEntry>

          <TimelineEntry 
            type="VIRTUAL CALL"
            date="Oct 21, 10:00 AM"
            title="Onboarding Kickoff for Logistics Team"
            risk="NEUTRAL RISK"
            riskColor="text-secondary"
            accentColor="bg-outline-variant border-outline-variant"
          >
            <p className="text-sm text-on-surface-variant leading-relaxed mb-4">
              Transcript shows high engagement from the operations manager. Positive sentiment regarding the new dashboard interface.
            </p>
            <div className="p-4 bg-surface-container-low rounded-lg">
              <p className="text-[10px] font-bold text-secondary uppercase tracking-wider mb-2">Intent Analysis</p>
              <p className="text-xs font-semibold text-primary">Process Alignment & Feature Validation</p>
            </div>
          </TimelineEntry>

          <TimelineEntry 
            type="SIGNAL DETECTED"
            date="Oct 18, 11:30 AM"
            title="Unmet Need: International Compliance Tools"
            content="we're actually expanding into the EU markets next month. If the platform could handle the VAT documentation automatically, that would be a game changer for us."
            risk="OPPORTUNITY"
            riskColor="text-success"
            accentColor="bg-secondary border-secondary"
          >
            <div className="flex flex-col gap-3">
              <p className="text-[10px] font-bold text-secondary uppercase tracking-wider">Cross-Sell Potential</p>
              <div className="flex flex-wrap gap-2">
                <span className="text-[10px] bg-white px-2 py-1 rounded border border-outline-variant/30 font-medium italic">EU Module</span>
                <span className="text-[10px] bg-white px-2 py-1 rounded border border-outline-variant/30 font-medium italic">VAT Automation</span>
              </div>
              <button className="w-full text-primary border border-primary/20 py-2.5 rounded-lg text-xs font-bold hover:bg-surface-variant transition-colors mt-2">
                Add to Pipeline
              </button>
            </div>
          </TimelineEntry>
        </div>
      </div>

      <div className="mt-12 pt-12 border-t border-outline-variant/20 flex justify-center">
        <button className="group flex items-center gap-3 text-secondary font-bold font-headline text-sm tracking-tighter uppercase">
          Load More Interactions
          <span className="material-symbols-outlined group-hover:translate-y-1 transition-transform">keyboard_arrow_down</span>
        </button>
      </div>
    </div>
  );
};

export default Timeline;
