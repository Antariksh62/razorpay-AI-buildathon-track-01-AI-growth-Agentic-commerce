import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, ShieldAlert, CheckCircle2, Sparkles, AlertCircle, ShieldCheck, Tag, Copy, Check, ShoppingBag, X, ArrowRight, ExternalLink, ShieldX } from 'lucide-react';
import { sendChatMessage, getCatalog } from '../services/api';
import StagedCart from './StagedCart';

// Helper component for markdown rendering in light mode
function FormattedMarkdown({ text }) {
  if (!text) return null;
  const paragraphs = text.split(/\n\n+/);
  
  return (
    <div className="space-y-2 text-xs leading-relaxed text-slate-800 font-sans">
      {paragraphs.map((paragraph, pIdx) => {
        const lines = paragraph.split('\n');
        return (
          <div key={pIdx} className="space-y-1">
            {lines.map((line, lIdx) => {
              const trimmed = line.trim();
              if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                const itemContent = trimmed.substring(2);
                return (
                  <div key={lIdx} className="flex items-start gap-2 pl-1.5">
                    <span className="text-blue-600 mt-0.5 text-[10px]">•</span>
                    <span className="flex-1">{parseInlineMarkdown(itemContent)}</span>
                  </div>
                );
              }
              return (
                <p key={lIdx}>
                  {parseInlineMarkdown(line)}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

function parseInlineMarkdown(text) {
  const parts = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="font-semibold text-slate-900">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={match.index} className="font-mono-code bg-slate-100 px-1.5 py-0.5 rounded text-[11px] text-blue-700 border border-slate-200">
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

export default function ChatInterface({ activeMandate, onMessageSent }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: "👋 Welcome! I am your **Razorpay Agentic Commerce Assistant**. I can discover products in the catalog, generate cart quotes, and execute policy-bounded Razorpay checkouts end-to-end.",
      timestamp: new Date().toLocaleTimeString(),
      verdict: 'ALLOWED'
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [copiedOrderId, setCopiedOrderId] = useState(null);
  const [isCatalogOpen, setIsCatalogOpen] = useState(false);
  const [catalogItems, setCatalogItems] = useState([]);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleOpenCatalog = async () => {
    setIsCatalogOpen(true);
    try {
      const data = await getCatalog();
      setCatalogItems(data);
    } catch (err) {
      console.error('Failed to load merchant catalog', err);
    }
  };

  const handleSend = async (customPrompt) => {
    const promptToUse = customPrompt || input;
    if (!promptToUse.trim() || loading) return;

    const userMsg = {
      sender: 'user',
      text: promptToUse,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customPrompt) setInput('');
    setLoading(true);

    try {
      const data = await sendChatMessage(promptToUse, activeMandate?.nonce);
      
      const agentMsg = {
        sender: 'agent',
        text: data.response_text,
        action_taken: data.action_taken,
        verdict: data.policy_verdict,
        orderId: data.razorpay_order_id,
        stagedCart: data.quote || null,
        timestamp: new Date().toLocaleTimeString()
      };

      setMessages((prev) => [...prev, agentMsg]);
      if (onMessageSent) onMessageSent(data);
    } catch (err) {
      console.error('Chat API Error:', err);
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: "❌ Error processing request. Make sure the FastAPI backend is running on `http://127.0.0.1:8000`.",
          verdict: 'ERROR',
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const copyOrderId = (orderId) => {
    navigator.clipboard.writeText(orderId);
    setCopiedOrderId(orderId);
    setTimeout(() => setCopiedOrderId(null), 2000);
  };

  const getRuleTriggeredText = (verdict) => {
    switch (verdict) {
      case 'ALLOWED':
      case 'SUCCESS':
        return 'Policy Authorization Granted';
      case 'BUDGET_BREACH':
        return 'Budget Breach Ceiling Guardrail';
      case 'REPLAY_ATTACK':
        return 'Anti-Replay Protection (Nonce Consumed)';
      case 'MANDATE_EXPIRED':
        return 'Mandate Temporal Expiry Window';
      case 'MANDATE_REVOKED':
        return 'Emergency Kill Switch Active (Mandate Revoked)';
      case 'STOCKOUT':
        return 'Stockout Guardrail';
      default:
        return verdict || 'Policy Rule Evaluation';
    }
  };

  return (
    <div className="flex flex-col h-full bg-white relative">
      {/* Panel Header */}
      <div className="bg-slate-50 px-5 py-3 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></div>
          <Bot className="w-4 h-4 text-blue-600" />
          <h2 className="font-semibold text-slate-800 text-xs tracking-wide">
            Buyer Agent Interface
          </h2>
        </div>

        {/* Catalog Preview Drawer Button */}
        <button
          onClick={handleOpenCatalog}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer shadow-xs"
        >
          <ShoppingBag className="w-3.5 h-3.5 text-blue-600" />
          <span>View Merchant Catalog</span>
        </button>
      </div>

      {/* Interactive Evaluation Scenario Chips Bar */}
      <div className="bg-slate-50/70 px-4 py-2 border-b border-slate-200 flex items-center gap-3 overflow-x-auto">
        <div className="flex items-center gap-1.5 shrink-0">
          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
          <p className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
            Evaluation Scenarios:
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Chip 1: Success Order */}
          <button
            type="button"
            onClick={() => handleSend("Buy AcousticBass Wireless Earphones within my budget")}
            disabled={loading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white hover:bg-emerald-50 border border-emerald-200 hover:border-emerald-400 text-[11px] font-semibold text-slate-800 hover:text-emerald-800 transition-all group shrink-0 cursor-pointer shadow-xs disabled:opacity-50"
          >
            <CheckCircle2 className="w-3 h-3 text-emerald-600 group-hover:scale-110 transition-transform" />
            <span>1. Success Order</span>
          </button>

          {/* Chip 2: Budget Breach */}
          <button
            type="button"
            onClick={() => handleSend("Buy Chronos Smart Watch Pro")}
            disabled={loading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white hover:bg-rose-50 border border-rose-200 hover:border-rose-400 text-[11px] font-semibold text-slate-800 hover:text-rose-800 transition-all group shrink-0 cursor-pointer shadow-xs disabled:opacity-50"
          >
            <ShieldAlert className="w-3 h-3 text-rose-600 group-hover:scale-110 transition-transform" />
            <span>2. Budget Breach</span>
          </button>

          {/* Chip 3: Stockout Handling */}
          <button
            type="button"
            onClick={() => handleSend("Buy AcousticBass Noise Cancelling Headphones")}
            disabled={loading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white hover:bg-amber-50 border border-amber-200 hover:border-amber-400 text-[11px] font-semibold text-slate-800 hover:text-amber-800 transition-all group shrink-0 cursor-pointer shadow-xs disabled:opacity-50"
          >
            <AlertCircle className="w-3 h-3 text-amber-600 group-hover:scale-110 transition-transform" />
            <span>3. Stockout</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 max-w-[90%] ${
              msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
                msg.sender === 'user'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-blue-600 text-white shadow-xs'
              }`}
            >
              {msg.sender === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
            </div>

            {/* Message Card */}
            <div
              className={`text-xs leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-2xl rounded-tr-none px-4 py-3 shadow-xs border border-blue-700/20'
                  : 'bg-white border border-slate-200 border-l-4 border-l-blue-600 text-slate-800 rounded-2xl rounded-tl-none p-4 shadow-sm'
              }`}
            >
              {/* Formatted Message Content */}
              {msg.sender === 'user' ? (
                <div className="whitespace-pre-wrap font-sans text-white font-medium">
                  {msg.text}
                </div>
              ) : (
                <FormattedMarkdown text={msg.text} />
              )}

              {/* STAGED MULTI-ITEM CART CARD */}
              {msg.stagedCart && <StagedCart stagedCart={msg.stagedCart} />}

              {/* SUCCESS RECEIPT CARD (Green Tinted Structured Component) */}
              {msg.orderId && (
                <div className="mt-3.5 bg-emerald-50/90 text-emerald-950 p-4 rounded-xl shadow-xs border border-emerald-200 space-y-3 font-sans">
                  <div className="flex items-center justify-between border-b border-emerald-200 pb-2.5">
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded-lg bg-emerald-100 text-emerald-700 border border-emerald-300">
                        <CheckCircle2 className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-[11px] font-bold tracking-wide uppercase block text-emerald-900">
                          Razorpay Order Success Receipt
                        </span>
                        <span className="text-[10px] text-emerald-700 font-mono">
                          Track 01 • Agentic Commerce Checkout
                        </span>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full uppercase">
                      PAID (TEST MODE)
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="bg-white p-2.5 rounded-lg border border-emerald-200 shadow-xs">
                      <span className="text-emerald-700 block text-[10px] font-mono uppercase">Product Name</span>
                      <span className="font-semibold text-emerald-950 line-clamp-2">
                        {msg.stagedCart?.item_name || 'Product Order'}
                      </span>
                    </div>

                    <div className="bg-white p-2.5 rounded-lg border border-emerald-200 shadow-xs">
                      <span className="text-emerald-700 block text-[10px] font-mono uppercase">Price Paid</span>
                      <span className="font-bold text-emerald-700 font-mono text-xs">
                        ₹{(msg.stagedCart?.total_amount_inr || msg.stagedCart?.price_inr || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between bg-white p-2.5 rounded-lg border border-emerald-200 text-[11px] font-mono shadow-xs">
                    <span className="text-emerald-700 text-[10px]">Razorpay Order ID:</span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => copyOrderId(msg.orderId)}
                        className="flex items-center gap-1.5 text-slate-700 hover:text-blue-700 font-semibold transition-colors group cursor-pointer"
                      >
                        <span>{msg.orderId}</span>
                        {copiedOrderId === msg.orderId ? (
                          <Check className="w-3 h-3 text-emerald-600" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-400 group-hover:text-blue-700" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (msg.orderId?.startsWith('order_test_')) {
                            alert(`Local Test Order (${msg.orderId}). Live Razorpay API credentials are required in backend .env to view deep-linked order pages. Opening Razorpay Merchant Dashboard...`);
                            window.open('https://dashboard.razorpay.com/app/orders', '_blank');
                          } else {
                            window.open(`https://dashboard.razorpay.com/app/orders/${msg.orderId}`, '_blank');
                          }
                        }}
                        className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 font-sans text-[10px] font-medium transition-colors cursor-pointer"
                        title="Open order in official Razorpay Merchant Dashboard"
                      >
                        <ExternalLink className="w-3 h-3 text-blue-600" />
                        <span>Razorpay Dashboard</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* BLOCKED RECEIPT CARD (Red/Amber Tinted Structured Component) */}
              {msg.verdict && msg.verdict !== 'ALLOWED' && msg.verdict !== 'SUCCESS' && msg.sender === 'agent' && (
                <div className={`mt-3.5 p-4 rounded-xl shadow-xs border space-y-3 font-sans ${
                  msg.verdict === 'BUDGET_BREACH' || msg.verdict === 'REPLAY_ATTACK' || msg.verdict === 'MANDATE_EXPIRED'
                    ? 'bg-rose-50/90 border-rose-200 text-rose-950'
                    : 'bg-amber-50/90 border-amber-200 text-amber-950'
                }`}>
                  <div className="flex items-center justify-between border-b border-rose-200 pb-2.5">
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded-lg bg-rose-100 text-rose-700 border border-rose-300">
                        <ShieldX className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-[11px] font-bold tracking-wide uppercase block text-rose-900">
                          Transaction Intercepted & Blocked
                        </span>
                        <span className="text-[10px] text-rose-700 font-mono">
                          Declarative Policy Hook Guardrail
                        </span>
                      </div>
                    </div>

                    <span className="text-[10px] font-mono font-bold bg-rose-100 text-rose-800 border border-rose-300 px-2 py-0.5 rounded-full uppercase">
                      INTERCEPTED BY POLICY ENGINE
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs">
                      <span className="text-slate-500 block text-[10px] font-mono uppercase tracking-wider mb-0.5">
                        Exact Rule Triggered
                      </span>
                      <span className="text-rose-700 font-sans font-bold text-[11px]">
                        {getRuleTriggeredText(msg.verdict)}
                      </span>
                    </div>

                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs">
                      <span className="text-slate-500 block text-[10px] font-mono uppercase tracking-wider mb-0.5">
                        Mandate Nonce Used
                      </span>
                      <span className="text-slate-800 font-mono-code font-medium text-[11px]">
                        {activeMandate?.nonce || 'MANDATE-DEMO'} ({activeMandate?.is_used ? 'Consumed' : 'Active'})
                      </span>
                    </div>

                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs sm:col-span-2 flex items-center justify-between">
                      <div>
                        <span className="text-slate-500 block text-[10px] font-mono uppercase tracking-wider">
                          Interception Layer
                        </span>
                        <span className="text-indigo-700 font-semibold font-sans text-[11px]">
                          Declarative Policy Hook Engine
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        FastAPI Safety Gate
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div className={`mt-2.5 text-[10px] font-mono ${
                msg.sender === 'user' ? 'text-blue-100' : 'text-slate-400'
              } text-right`}>
                {msg.timestamp}
              </div>
            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {loading && (
          <div className="flex gap-3 mr-auto items-center">
            <div className="w-7 h-7 rounded-xl bg-blue-600 flex items-center justify-center text-white shrink-0 shadow-xs">
              <Bot className="w-3.5 h-3.5 animate-spin" />
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none px-4 py-3 text-xs text-slate-700 flex items-center gap-2.5 shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600"></span>
              </span>
              <span className="font-sans font-medium">Evaluating policy hooks & catalog check...</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Merchant Catalog Side Drawer Modal */}
      {isCatalogOpen && (
        <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs z-30 flex justify-end">
          <div className="w-full max-w-sm bg-white h-full shadow-2xl border-l border-slate-200 flex flex-col animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-xs">Merchant Inventory Catalog</h3>
              </div>
              <button
                onClick={() => setIsCatalogOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Drawer Inventory List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {catalogItems.length === 0 ? (
                <p className="text-xs text-slate-500 font-sans">Loading catalog items...</p>
              ) : (
                catalogItems.map((item) => (
                  <div
                    key={item.item_id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 hover:border-blue-300 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-semibold text-slate-900 text-xs">{item.name}</h4>
                        <span className="text-[10px] font-mono text-slate-400">{item.item_id}</span>
                      </div>
                      <span className="font-bold text-xs text-emerald-700 font-mono bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        ₹{item.price_inr.toLocaleString('en-IN')}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 leading-relaxed font-sans">
                      {item.description}
                    </p>

                    <div className="flex items-center justify-between pt-1 border-t border-slate-200 text-[11px]">
                      <span className={`font-mono font-medium text-[10px] ${
                        item.stock > 0 ? 'text-emerald-700' : 'text-rose-700 font-bold'
                      }`}>
                        {item.stock > 0 ? `In Stock (${item.stock})` : 'OUT OF STOCK (Stock: 0)'}
                      </span>

                      <button
                        onClick={() => {
                          setIsCatalogOpen(false);
                          handleSend(`Buy ${item.name}`);
                        }}
                        className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors cursor-pointer"
                      >
                        <span>Prompt AI</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Input Box */}
      <div className="p-3 bg-white border-t border-slate-200">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2 bg-slate-50 border border-slate-200 focus-within:border-blue-500 focus-within:bg-white rounded-xl p-1.5 transition-all shadow-xs"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask AI agent to buy products, search catalog, or test budget rules..."
            className="flex-1 bg-transparent px-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none font-sans"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white p-2 rounded-lg transition-all shadow-xs cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
