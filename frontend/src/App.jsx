import React, { useState, useEffect } from 'react';
import MandateConfig from './components/MandateConfig';
import ChatInterface from './components/ChatInterface';
import AuditConsole from './components/AuditConsole';
import { getMandate } from './services/api';

export default function App() {
  const [activeMandate, setActiveMandate] = useState(null);

  useEffect(() => {
    getMandate()
      .then((data) => setActiveMandate(data))
      .catch((err) => console.error('Failed to load active mandate', err));
  }, []);

  const handleMandateChange = (newMandate) => {
    setActiveMandate(newMandate);
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-dashboard-mesh-light bg-slate-50 text-slate-900 font-sans antialiased">
      {/* Top Header & Active Authorization Card */}
      <MandateConfig
        activeMandate={activeMandate}
        onMandateChange={handleMandateChange}
      />

      {/* Main Split-Screen SaaS Dashboard */}
      <main className="flex-1 grid grid-cols-1 md:grid-cols-2 overflow-hidden border-t border-slate-200">
        {/* Left Panel: Chat Interface */}
        <section className="h-full overflow-hidden border-r border-slate-200 bg-white">
          <ChatInterface
            activeMandate={activeMandate}
            onMessageSent={() => {
              // Refresh mandate status after chat execution
              getMandate().then(setActiveMandate).catch(() => {});
            }}
          />
        </section>

        {/* Right Panel: Live Audit Terminal */}
        <section className="h-full overflow-hidden bg-slate-50/60">
          <AuditConsole />
        </section>
      </main>
    </div>
  );
}
