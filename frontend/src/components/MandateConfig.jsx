import React, { useState, useEffect } from 'react';
import { ShieldCheck, Lock, Zap, Key, Copy, Check, RefreshCw, ShieldOff, AlertOctagon, ArrowRight } from 'lucide-react';
import { updateMandate, refreshMandate, revokeMandate } from '../services/api';

export default function MandateConfig({ activeMandate, onMandateChange }) {
  const [maxSpend, setMaxSpend] = useState(2000);
  const [customCapInput, setCustomCapInput] = useState('');
  const [duration, setDuration] = useState(60);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    if (activeMandate) {
      setMaxSpend(activeMandate.max_spend_inr);
    }
  }, [activeMandate]);

  const handleUpdate = async (newSpend) => {
    const spendToSet = newSpend !== undefined ? newSpend : maxSpend;
    setLoading(true);
    setSuccessMsg('');
    try {
      const updated = await updateMandate(spendToSet, duration);
      onMandateChange(updated);
      setSuccessMsg(`Authorization cap updated to ₹${parseFloat(spendToSet).toLocaleString('en-IN')}`);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      console.error('Failed to update mandate', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    setSuccessMsg('');
    try {
      const fresh = await refreshMandate(maxSpend, duration);
      onMandateChange(fresh);
      setSuccessMsg(`Fresh Mandate ${fresh.nonce} Generated!`);
      setTimeout(() => setSuccessMsg(''), 3500);
    } catch (err) {
      console.error('Failed to refresh mandate', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async () => {
    setLoading(true);
    setSuccessMsg('');
    try {
      const revoked = await revokeMandate(rawNonce);
      onMandateChange(revoked);
      setSuccessMsg(`EMERGENCY KILL SWITCH: Mandate ${rawNonce} REVOKED!`);
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      console.error('Failed to revoke mandate', err);
    } finally {
      setLoading(false);
    }
  };

  const rawNonce = activeMandate?.nonce || '0x1787f3b892a019e4280';
  
  const truncatedNonce = rawNonce.length > 13 
    ? `${rawNonce.slice(0, 6)}...${rawNonce.slice(-4)}`
    : rawNonce;

  const handleCopyNonce = () => {
    navigator.clipboard.writeText(rawNonce);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const currentSpend = activeMandate?.current_spend_inr || 0;
  const maxCap = activeMandate?.max_spend_inr || maxSpend;
  const remainingSpend = Math.max(0, maxCap - currentSpend);
  const utilizationPct = Math.min(100, Math.round((currentSpend / maxCap) * 100));

  const isRevoked = activeMandate?.is_used === -1;
  const isConsumed = currentSpend >= maxCap || activeMandate?.is_used === 1;
  const isExpired = activeMandate?.expires_at && new Date(activeMandate.expires_at) < new Date();
  
  let statusText = 'ACTIVE';
  let statusColor = 'emerald';

  if (isRevoked) {
    statusText = 'REVOKED';
    statusColor = 'rose';
  } else if (isConsumed) {
    statusText = 'EXHAUSTED';
    statusColor = 'rose';
  } else if (isExpired) {
    statusText = 'EXPIRED';
    statusColor = 'amber';
  }

  return (
    <header className="w-full bg-white border-b border-slate-200 px-6 py-2.5 flex items-center justify-between gap-6 shadow-xs z-20">
      {/* 1. Simple Clean Header Title */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-blue-600 text-white shadow-xs font-bold text-xs">
          <ShieldCheck className="w-4 h-4" />
        </div>
        <h1 className="font-bold text-sm text-slate-900 font-sans tracking-tight">
          Razorpay Agentic Commerce
        </h1>
      </div>

      {/* 2. Prominent & Large Spend Timeline Progress Bar */}
      <div className="flex-1 max-w-sm bg-slate-50 border border-slate-200 px-3.5 py-1.5 rounded-xl shadow-xs flex flex-col gap-1">
        <div className="flex items-center justify-between text-[11px] font-sans">
          <span className="text-slate-500 font-medium">Spend Utilization</span>
          <span className="font-mono font-bold text-slate-900">{utilizationPct}%</span>
        </div>
        <div className="w-full h-2 bg-slate-200/80 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              utilizationPct >= 100 ? 'bg-rose-500' : utilizationPct >= 80 ? 'bg-amber-500' : 'bg-blue-600'
            }`}
            style={{ width: `${utilizationPct}%` }}
          ></div>
        </div>
        <div className="flex items-center justify-between text-[10px] font-mono">
          <span className="text-slate-600 font-medium">₹{currentSpend.toLocaleString('en-IN')} spent</span>
          <span className="text-emerald-700 font-bold">₹{remainingSpend.toLocaleString('en-IN')} remaining</span>
        </div>
      </div>

      {/* 3. Full-Width Control Actions Navbar */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Copyable Nonce Badge */}
        <div className="flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl shadow-xs">
          <Key className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-500 text-[11px]">Nonce:</span>
          <button
            onClick={handleCopyNonce}
            title={`Click to copy full nonce: ${rawNonce}`}
            className="flex items-center gap-1.5 font-mono text-[11px] font-medium text-slate-700 bg-white hover:bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 transition-colors shadow-xs group cursor-pointer"
          >
            <span>{truncatedNonce}</span>
            {copied ? (
              <Check className="w-3 h-3 text-emerald-600" />
            ) : (
              <Copy className="w-3 h-3 text-slate-400 group-hover:text-slate-600 transition-colors" />
            )}
          </button>
        </div>

        {/* Generate / Refresh Fresh Mandate Button */}
        <button
          onClick={handleRefresh}
          disabled={loading}
          title="Mint a fresh active intent mandate nonce"
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-sans font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-xl transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-600 ${loading ? 'animate-spin' : ''}`} />
          <span>Mint Fresh Mandate</span>
        </button>

        {/* Red Emergency Kill Switch Button */}
        <button
          onClick={handleRevoke}
          disabled={loading || isRevoked}
          title="Revoke mandate access immediately (Emergency Kill Switch)"
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-sans font-semibold rounded-xl transition-all cursor-pointer disabled:opacity-50 shadow-xs ${
            isRevoked
              ? 'bg-rose-100 text-rose-800 border border-rose-300'
              : 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
          }`}
        >
          <ShieldOff className="w-3.5 h-3.5 text-rose-600" />
          <span>{isRevoked ? 'Mandate Revoked' : 'Revoke Access'}</span>
        </button>

        {/* Custom Spend Cap Input Form */}
        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl shadow-xs">
          <Lock className="w-3.5 h-3.5 text-emerald-600" />
          <span className="text-slate-500 font-medium text-[11px]">Cap:</span>
          
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const val = parseFloat(customCapInput);
              if (!isNaN(val) && val > 0) {
                handleUpdate(val);
                setCustomCapInput('');
              }
            }}
            className="flex items-center bg-white border border-slate-200 rounded-lg p-0.5 shadow-xs hover:border-blue-300 focus-within:border-blue-500 transition-colors"
          >
            <span className="pl-1.5 pr-0.5 text-[10px] font-mono text-slate-400 font-bold">₹</span>
            <input
              type="number"
              min="100"
              step="100"
              placeholder={`${maxCap.toLocaleString('en-IN')}`}
              value={customCapInput}
              onChange={(e) => setCustomCapInput(e.target.value)}
              className="w-20 text-[11px] font-mono font-medium text-slate-900 placeholder-slate-400 focus:outline-none bg-transparent"
            />
            <button
              type="submit"
              disabled={loading || !customCapInput.trim()}
              title="Apply custom spend cap"
              className="text-[10px] font-sans font-semibold px-2 py-0.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer disabled:opacity-40 shadow-xs flex items-center gap-0.5"
            >
              <span>Set Cap</span>
              <ArrowRight className="w-2.5 h-2.5" />
            </button>
          </form>
        </div>

        {/* Status Indicator Dot */}
        <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl shadow-xs">
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
              statusColor === 'emerald' ? 'bg-emerald-400' : statusColor === 'amber' ? 'bg-amber-400' : 'bg-rose-500'
            }`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${
              statusColor === 'emerald' ? 'bg-emerald-500' : statusColor === 'amber' ? 'bg-amber-500' : 'bg-rose-600'
            }`}></span>
          </span>
          <span className={`text-[11px] font-mono font-bold tracking-wider uppercase px-2 py-0.5 rounded-md border ${
            statusColor === 'emerald'
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : statusColor === 'amber'
              ? 'bg-amber-50 text-amber-700 border-amber-200'
              : 'bg-rose-100 text-rose-800 border-rose-300 font-bold'
          }`}>
            {statusText}
          </span>
        </div>
      </div>

      {/* Success / Revocation Notification Toast */}
      {successMsg && (
        <div className={`text-xs px-3 py-1.5 rounded-xl animate-fade-in flex items-center gap-1.5 font-sans font-medium shadow-xs border fixed bottom-4 right-4 z-50 ${
          isRevoked || successMsg.includes('REVOKED')
            ? 'bg-rose-50 text-rose-800 border-rose-200'
            : 'bg-emerald-50 text-emerald-800 border-emerald-200'
        }`}>
          {isRevoked || successMsg.includes('REVOKED') ? (
            <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />
          ) : (
            <Zap className="w-3.5 h-3.5 text-emerald-600" />
          )}
          {successMsg}
        </div>
      )}
    </header>
  );
}
