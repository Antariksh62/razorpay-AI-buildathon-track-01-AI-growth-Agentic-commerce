import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Shield, CheckCircle2, XCircle, AlertTriangle, Pause, Play, Trash2, Activity } from 'lucide-react';
import { subscribeAuditStream, getAuditLogs } from '../services/api';

export default function AuditConsole() {
  const [logs, setLogs] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const consoleEndRef = useRef(null);

  useEffect(() => {
    // Load initial logs
    getAuditLogs(30)
      .then((data) => {
        if (Array.isArray(data)) {
          setLogs(data.reverse());
        }
      })
      .catch((err) => console.error('Failed to load initial audit logs', err));

    // Connect to SSE stream
    const unsubscribe = subscribeAuditStream((newLog) => {
      setLogs((prev) => {
        if (prev.some((log) => log.id === newLog.id)) {
          return prev;
        }
        return [...prev, newLog];
      });
    });

    return () => {
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (autoScroll) {
      consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const renderVerdictBadge = (verdict) => {
    const vUpper = (verdict || '').toUpperCase();
    if (vUpper === 'ALLOWED' || vUpper === 'SUCCESS' || vUpper === 'PASS') {
      return (
        <span className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-200">
          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
          PASS
        </span>
      );
    }
    if (
      vUpper === 'BUDGET_BREACH' ||
      vUpper === 'REPLAY_ATTACK' ||
      vUpper === 'MANDATE_EXPIRED' ||
      vUpper === 'MANDATE_NOT_FOUND' ||
      vUpper === 'BLOCKED' ||
      vUpper === 'REJECTED'
    ) {
      return (
        <span className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-rose-100 text-rose-800 border border-rose-200">
          <XCircle className="w-3 h-3 text-rose-600" />
          BLOCKED
        </span>
      );
    }
    if (vUpper === 'STOCKOUT' || vUpper === 'WARNING') {
      return (
        <span className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 border border-amber-200">
          <AlertTriangle className="w-3 h-3 text-amber-600" />
          STOCKOUT
        </span>
      );
    }

    return (
      <span className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-indigo-100 text-indigo-800 border border-indigo-200">
        <Shield className="w-3 h-3 text-indigo-600" />
        {verdict}
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full bg-slate-50/50 font-mono-code text-xs">
      {/* Console Top Bar */}
      <div className="bg-slate-100/90 px-4 py-3 border-b border-slate-200 flex items-center justify-between shadow-xs">
        {/* Left: Console Title */}
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-indigo-600" />
          <h2 className="font-semibold text-slate-800 text-xs font-sans tracking-wide">
            Live Audit Stream Console
          </h2>
        </div>

        {/* Right: Working Console Action Controls */}
        <div className="flex items-center gap-2 font-sans text-xs">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-mono transition-all cursor-pointer shadow-xs ${
              autoScroll
                ? 'bg-white text-indigo-700 border-indigo-200 font-medium'
                : 'bg-white text-slate-500 border-slate-200 hover:text-slate-800'
            }`}
          >
            {autoScroll ? <Pause className="w-3 h-3 text-indigo-600" /> : <Play className="w-3 h-3" />}
            <span>{autoScroll ? 'Autoscroll On' : 'Paused'}</span>
          </button>

          <button
            onClick={() => setLogs([])}
            className="p-1 text-slate-400 hover:text-rose-600 bg-white border border-slate-200 hover:border-rose-300 rounded-md transition-colors cursor-pointer shadow-xs"
            title="Clear Audit Logs"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Body */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-2 bg-slate-50/30">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 py-12">
            <Activity className="w-8 h-8 mb-2.5 opacity-40 text-indigo-500 animate-pulse" />
            <p className="text-xs font-sans text-slate-500 font-medium">Awaiting real-time policy audit stream events...</p>
          </div>
        ) : (
          logs.map((log) => {
            const formattedTime = new Date(log.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              hour12: false
            });

            return (
              <div
                key={log.id}
                className="bg-white border border-slate-200/90 hover:border-slate-300 p-2.5 rounded-lg transition-all space-y-1.5 shadow-xs group"
              >
                {/* Event Header Line */}
                <div className="flex items-center justify-between gap-2 text-[11px]">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono text-[10px]">[{formattedTime}]</span>
                    <span className="text-indigo-600 font-semibold font-mono text-[11px]">
                      {log.action}
                    </span>
                  </div>

                  {/* Light Pill Verdict Tag */}
                  {renderVerdictBadge(log.policy_verdict)}
                </div>

                {/* Event Detail Line */}
                <p className="text-[11px] text-slate-700 font-mono-code leading-relaxed break-words pl-1 border-l border-slate-200">
                  {log.details}
                </p>
              </div>
            );
          })
        )}
        <div ref={consoleEndRef} />
      </div>

      {/* Terminal Footer Status */}
      <div className="bg-white border-t border-slate-200 px-4 py-2 flex items-center justify-between text-[11px] font-sans shadow-xs">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-emerald-700 font-mono font-semibold text-[10px] tracking-wider uppercase">
            STREAMING LIVE
          </span>
          <span className="text-slate-400 text-[10px] font-mono">• {logs.length} events logged</span>
        </div>

        <span className="text-[10px] font-mono text-slate-400">
          ACID Compliance: WAL Mode
        </span>
      </div>
    </div>
  );
}
