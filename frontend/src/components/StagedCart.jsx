import React from 'react';
import { ShoppingBag, Package, ShieldCheck, Tag } from 'lucide-react';

export default function StagedCart({ stagedCart }) {
  if (!stagedCart || !stagedCart.items || stagedCart.items.length === 0) return null;

  const { quote_id, items, total_amount_inr, is_multi_item } = stagedCart;

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3 my-2 max-w-md text-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-blue-100 border border-blue-200 text-blue-600 shadow-xs">
            <ShoppingBag className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 font-sans tracking-tight">
              {is_multi_item ? 'Staged Multi-Item Cart Quote' : 'Staged Product Quote'}
            </h4>
            <p className="text-[10px] text-slate-500 font-mono">ID: {quote_id}</p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
          {items.length} {items.length === 1 ? 'Item' : 'Items'}
        </span>
      </div>

      {/* Itemized List */}
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div
            key={item.item_id || idx}
            className="flex items-center justify-between bg-white border border-slate-200 p-2.5 rounded-xl text-xs shadow-2xs"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <Package className="w-4 h-4 text-slate-400 shrink-0" />
              <div className="truncate">
                <p className="font-semibold text-slate-900 truncate font-sans text-[11px]">
                  {item.name}
                </p>
                <p className="text-[10px] text-slate-500 font-mono">
                  ₹{item.price_inr?.toLocaleString('en-IN')} × {item.quantity}
                </p>
              </div>
            </div>
            <div className="text-right shrink-0">
              <span className="font-mono font-bold text-slate-900 text-xs">
                ₹{item.subtotal_inr?.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Aggregate Summary Footer */}
      <div className="border-t border-slate-200 pt-2.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 text-slate-600 text-[11px]">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Aggregate Cart Total:</span>
        </div>
        <span className="font-mono font-extrabold text-sm text-slate-900">
          ₹{total_amount_inr?.toLocaleString('en-IN')}
        </span>
      </div>
    </div>
  );
}
