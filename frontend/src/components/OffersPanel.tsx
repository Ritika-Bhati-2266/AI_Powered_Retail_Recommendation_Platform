import { useState, useEffect } from 'react';
import { Gift, CalendarDays, AlertTriangle } from 'lucide-react';
import { apiClient } from '../api/client';
import type { Offer } from '../types';

interface OffersPanelProps {
  customerId: string;
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

function formatDiscount(discountType: string, discountValue: number): string {
  // "fixed" type with value 0 means free shipping
  if (discountType === 'fixed' && discountValue === 0) {
    return 'FREE SHIPPING';
  }
  switch (discountType) {
    case 'percentage':
      return `${discountValue}% OFF`;
    case 'fixed_amount':
      return `$${discountValue.toFixed(2)} OFF`;
    case 'fixed':
      return `$${discountValue.toFixed(2)} OFF`;
    case 'free_shipping':
      return 'FREE SHIPPING';
    case 'bogof':
      return 'BUY 1 GET 1';
    default:
      return `${discountValue} OFF`;
  }
}

export default function OffersPanel({ customerId }: OffersPanelProps) {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!customerId) return;

    setLoading(true);
    setError(null);

    apiClient
      .getOffers(customerId)
      .then(setOffers)
      .catch((err) => {
        setError(err.message || 'Failed to load offers');
        setOffers([]);
      })
      .finally(() => setLoading(false));
  }, [customerId]);

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
        Active Offers
      </h3>

      {loading && (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="bg-slate-800/50 rounded-lg p-4 space-y-2">
              <div className="skeleton h-5 w-3/4" />
              <div className="skeleton h-3 w-full" />
              <div className="skeleton h-3 w-1/3" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="text-center py-8">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm text-slate-400">Failed to load offers</p>
          <p className="text-xs text-slate-500 mt-1">{error}</p>
        </div>
      )}

      {!loading && !error && offers.length === 0 && (
        <div className="text-center py-8">
          <Gift className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No active offers for this customer</p>
        </div>
      )}

      {!loading && !error && offers.length > 0 && (
        <div className="space-y-3">
          {offers.map((offer) => (
            <div
              key={offer.offer_id}
              className="bg-slate-800/50 rounded-lg border border-amber-700/20 hover:border-amber-600/40 transition-all p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-slate-200">{offer.title}</h4>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{offer.description}</p>
                  <div className="flex items-center gap-1.5 mt-2 text-xs text-slate-500">
                    <CalendarDays className="w-3.5 h-3.5" />
                    <span>Valid until {formatDate(offer.valid_until)}</span>
                  </div>
                </div>
                <div className="shrink-0 bg-amber-900/30 border border-amber-700/40 rounded-lg px-3 py-2 text-center min-w-[100px]">
                  <p className="text-sm font-bold text-amber-400">
                    {formatDiscount(offer.discount_type, offer.discount_value)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
