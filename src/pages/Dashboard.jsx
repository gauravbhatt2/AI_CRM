import React from 'react';
import { motion as Motion } from 'framer-motion';

const KPICard = ({ title, value, subvalue, trend, icon, colorClass }) => (
  <Motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`bg-surface-container-lowest p-8 rounded-xl shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)] flex flex-col justify-between border-l-4 ${colorClass}`}
  >
    <div className="flex justify-between items-start">
      <span className="material-symbols-outlined text-primary-container">{icon}</span>
      {trend && (
        <span className={`text-[10px] font-black px-2 py-0.5 rounded text-xs ${
          trend.includes('+') ? 'bg-primary-container/10 text-primary' : 'bg-error-container text-on-error-container'
        }`}>
          {trend}
        </span>
      )}
    </div>
    <div className="mt-4">
      <p className="text-xs font-headline font-bold text-on-surface-variant uppercase tracking-tighter">{title}</p>
      <h3 className="text-3xl font-black font-headline text-primary mt-1">
        {value}
        {subvalue && <span className="text-lg opacity-40">{subvalue}</span>}
      </h3>
    </div>
  </Motion.div>
);

const Dashboard = () => {
  return (
    <div className="space-y-10">
      {/* Header Section */}
      <div className="flex justify-between items-end">
        <div className="max-w-2xl">
          <Motion.h2 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-4xl font-extrabold text-on-surface font-headline leading-tight"
          >
            Editorial Pulse
          </Motion.h2>
          <Motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-on-surface-variant font-body mt-2 text-lg"
          >
            AI insights are projecting a <span className="text-secondary font-bold">14% growth</span> in qualified deal velocity this quarter.
          </Motion.p>
        </div>
        <div className="flex gap-3">
          <button className="px-6 py-2.5 bg-surface-container-highest rounded-full text-primary font-headline font-bold text-xs uppercase tracking-widest hover:bg-surface-variant transition-all">
            Export Report
          </button>
          <Motion.button 
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="px-6 py-2.5 bg-primary text-on-primary rounded-full font-headline font-bold text-xs uppercase tracking-widest flex items-center gap-2 hover:shadow-lg shadow-primary/10 transition-all"
          >
            <span className="material-symbols-outlined text-sm">add</span> New Deal
          </Motion.button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard title="Total Records" value="24,812" trend="+12%" icon="storage" colorClass="border-primary" />
        <KPICard title="Avg Deal Score" value="84" subvalue="/100" trend="OPTIMAL" icon="analytics" colorClass="border-secondary" />
        <KPICard title="High Risk Deals" value="12" trend="CRITICAL" icon="warning" colorClass="border-tertiary-fixed-dim" />
        <KPICard title="Average Budget" value="$142.5k" trend="USD" icon="payments" colorClass="border-primary-container" />
      </div>

      {/* Main Grid Content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Budget Distribution Chart */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-low rounded-xl p-8 relative overflow-hidden h-[400px]">
          <div className="flex justify-between items-start mb-8 relative z-10">
            <div>
              <h4 className="text-xl font-bold font-headline">Budget Distribution</h4>
              <p className="text-sm text-on-surface-variant">Deal flow by fiscal quarter</p>
            </div>
            <div className="flex gap-4">
              <span className="flex items-center gap-1.5 text-xs font-bold text-primary">
                <span className="w-3 h-3 rounded-full bg-primary"></span> Enterprise
              </span>
              <span className="flex items-center gap-1.5 text-xs font-bold text-on-surface-variant">
                <span className="w-3 h-3 rounded-full bg-secondary"></span> Mid-Market
              </span>
            </div>
          </div>
          
          <div className="absolute bottom-0 left-0 right-0 h-48 px-8 flex items-end justify-between gap-4">
            {[24, 36, 16, 32, 44, 20, 38].map((h, i) => (
              <div key={i} className={`w-full bg-primary-container/10 h-${h > 40 ? '48' : h > 30 ? '40' : '28'} rounded-t-lg relative group transition-all`}>
                <Motion.div 
                  initial={{ height: 0 }}
                  animate={{ height: `${h * 2}px` }}
                  transition={{ delay: i * 0.1, duration: 1 }}
                  className={`absolute bottom-0 left-0 right-0 ${i % 3 === 0 ? 'bg-secondary' : 'bg-primary'} rounded-t-lg group-hover:opacity-80`}
                />
              </div>
            ))}
          </div>
        </div>

        {/* AI Command Center */}
        <div className="col-span-12 lg:col-span-4 bg-[#B38D97]/10 p-8 rounded-xl relative overflow-hidden flex flex-col">
          <div className="relative z-10">
            <div className="flex items-center gap-2 text-secondary mb-4">
              <span className="material-symbols-outlined">auto_awesome</span>
              <p className="font-headline font-bold text-xs uppercase tracking-widest">AI Command Center</p>
            </div>
            <h4 className="text-xl font-bold font-headline mb-4">Urgent Actions</h4>
            <div className="space-y-6">
              {[
                { title: 'High-risk interaction detected', desc: "Global Tech Corp's CTO expressed budget concerns.", color: 'bg-tertiary-fixed-dim', action: 'Draft Response' },
                { title: 'Follow-ups pending', desc: "3 enterprise leads haven't been contacted in 48h.", color: 'bg-secondary', action: 'View Leads' },
                { title: 'New Intent Spike', desc: "Apex Solutions visited pricing page 4 times today.", color: 'bg-primary', action: 'Assign SDR' }
              ].map((item, i) => (
                <Motion.div 
                  key={i}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                  className="flex gap-4 group cursor-pointer"
                >
                  <div className={`w-1 ${item.color} rounded-full transition-all group-hover:w-2`}></div>
                  <div>
                    <p className="text-sm font-bold text-on-surface">{item.title}</p>
                    <p className="text-xs text-on-surface-variant mt-1">{item.desc}</p>
                    <button className="mt-2 text-xs font-bold text-secondary uppercase tracking-wider hover:underline">
                      {item.action}
                    </button>
                  </div>
                </Motion.div>
              ))}
            </div>
          </div>
          <div className="absolute -right-4 -bottom-4 w-32 h-32 bg-secondary opacity-5 blur-3xl rounded-full"></div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)] h-80">
          <h4 className="text-lg font-bold font-headline mb-6">Intent Distribution</h4>
          <div className="flex items-center justify-between h-48">
            <div className="w-40 h-40 rounded-full border-[16px] border-primary-container relative flex items-center justify-center">
              <div className="absolute inset-0 border-[16px] border-secondary border-l-transparent border-b-transparent border-t-transparent rotate-[45deg]"></div>
              <div className="text-center">
                <p className="text-2xl font-black font-headline">72%</p>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase">High Intent</p>
              </div>
            </div>
            <div className="space-y-3 flex-1 ml-12">
              {[
                { label: 'Informational', value: '12%', color: 'bg-primary' },
                { label: 'Commercial', value: '48%', color: 'bg-secondary' },
                { label: 'Transactional', value: '24%', color: 'bg-primary-container' },
                { label: 'Other', value: '16%', color: 'bg-surface-variant' }
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-xs font-medium text-on-surface-variant">
                    <span className={`w-2 h-2 rounded-full ${item.color}`}></span> {item.label}
                  </span>
                  <span className="text-xs font-bold">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)] h-80 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h4 className="text-lg font-bold font-headline">Deal Score Distribution</h4>
            <span className="text-xs font-bold font-headline text-secondary tracking-widest uppercase">Benchmark: 78</span>
          </div>
          <div className="flex-1 flex items-end gap-1 px-2">
            {[20, 35, 65, 85, 50, 25, 10].map((h, i) => (
              <div 
                key={i} 
                className={`flex-1 ${i === 2 ? 'bg-primary' : i === 4 ? 'bg-secondary' : 'bg-surface-container-low'} rounded-t hover:bg-primary transition-colors cursor-pointer group relative`}
                style={{ height: `${h}%` }}
              >
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-primary text-on-primary text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                  {h}%
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-4 px-2">
            <span className="text-[10px] font-bold text-on-surface-variant uppercase">Weak</span>
            <span className="text-[10px] font-bold text-on-surface-variant uppercase">Mid</span>
            <span className="text-[10px] font-bold text-on-surface-variant uppercase">Strong</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
