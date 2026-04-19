import React from 'react';
import Layout from '../components/Layout';

const AIIntelligence = () => (
  <Layout>
    <div className="py-10">
      <h2 className="text-4xl font-extrabold text-primary font-headline tracking-tighter mb-4">AI Intelligence</h2>
      <p className="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
        Strategic neural processing of all incoming data streams. Identifying patterns that human intuition might overlook.
      </p>
      <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-surface-container-low p-8 rounded-xl border-l-4 border-secondary shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-secondary">psychology</span>
              <h4 className="font-bold text-primary font-headline italic">Neural Cluster {i}</h4>
            </div>
            <p className="text-sm text-on-surface-variant leading-loose">
              Analyzing deal velocity and sentiment markers across Enterprise segments in the EMEA region.
            </p>
          </div>
        ))}
      </div>
    </div>
  </Layout>
);

const Analytics = () => (
  <Layout>
    <div className="py-10 text-center">
      <h2 className="text-4xl font-extrabold text-primary font-headline tracking-tighter mb-4">Analytics</h2>
      <p className="text-on-surface-variant">Deep dive into the data metrics.</p>
    </div>
  </Layout>
);

const CRMRecords = () => (
  <Layout>
    <div className="py-10">
      <h2 className="text-4xl font-extrabold text-primary font-headline tracking-tighter mb-4">CRM Records</h2>
      <div className="bg-surface-container-lowest rounded-xl overflow-hidden shadow-sm border border-outline-variant/10 mt-8">
        <table className="w-full text-left">
          <thead className="bg-surface-container text-[10px] font-black uppercase tracking-widest text-[#424b54]/50">
            <tr>
              <th className="px-8 py-4">Account Name</th>
              <th className="px-8 py-4">Deal Value</th>
              <th className="px-8 py-4">Confidence</th>
              <th className="px-8 py-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/10 text-sm">
            {[
              { name: 'Global Logistics Corp', value: '$1.2M', confidence: '94%', status: 'Active' },
              { name: 'Apex Solutions', value: '$450k', confidence: '82%', status: 'Nurture' },
              { name: 'Veridian Systems', value: '$2.8M', confidence: '91%', status: 'Negotiation' },
            ].map((row, i) => (
              <tr key={i} className="hover:bg-surface-container-low transition-colors">
                <td className="px-8 py-4 font-bold text-primary">{row.name}</td>
                <td className="px-8 py-4">{row.value}</td>
                <td className="px-8 py-4 text-secondary font-bold">{row.confidence}</td>
                <td className="px-8 py-4 uppercase text-[10px] font-black">{row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </Layout>
);

export { AIIntelligence, Analytics, CRMRecords };
