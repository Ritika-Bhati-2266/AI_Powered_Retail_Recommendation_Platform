import { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  LogOut,
  Star,
  Package,
  Smartphone,
  Shirt,
  Sofa,
  BookOpen,
  Dumbbell,
  Gamepad2,
  Apple,
  Loader2,
  DollarSign,
} from 'lucide-react';
import { apiClient } from '../api/client';
import ProductSearch from './ProductSearch';
import { formatPrice } from '../utils/formatPrice';
import type { CustomerFull, Recommendation } from '../types';

// Reuse the category icon/color mapping from ProductSearch
const CATEGORY_ICONS: Record<string, typeof Smartphone> = {
  Electronics: Smartphone,
  Clothing: Shirt,
  'Home & Kitchen': Sofa,
  Books: BookOpen,
  Sports: Dumbbell,
  Toys: Gamepad2,
  Grocery: Apple,
  Beauty: Sparkles,
};

const CATEGORY_COLORS: Record<string, string> = {
  Electronics: 'from-cyan-500/20 to-cyan-600/10 border-cyan-700/30',
  Clothing: 'from-pink-500/20 to-pink-600/10 border-pink-700/30',
  'Home & Kitchen': 'from-amber-500/20 to-amber-600/10 border-amber-700/30',
  Books: 'from-emerald-500/20 to-emerald-600/10 border-emerald-700/30',
  Sports: 'from-blue-500/20 to-blue-600/10 border-blue-700/30',
  Beauty: 'from-purple-500/20 to-purple-600/10 border-purple-700/30',
  Toys: 'from-orange-500/20 to-orange-600/10 border-orange-700/30',
  Grocery: 'from-lime-500/20 to-lime-600/10 border-lime-700/30',
};

const CATEGORY_ICON_COLORS: Record<string, string> = {
  Electronics: 'text-cyan-400',
  Clothing: 'text-pink-400',
  'Home & Kitchen': 'text-amber-400',
  Books: 'text-emerald-400',
  Sports: 'text-blue-400',
  Beauty: 'text-purple-400',
  Toys: 'text-orange-400',
  Grocery: 'text-lime-400',
};

function getCategoryIcon(category: string) {
  return CATEGORY_ICONS[category] || Package;
}

function RecCard({ product }: { product: Recommendation }) {
  const Icon = getCategoryIcon(product.category);
  const colorClass = CATEGORY_COLORS[product.category] || 'from-slate-500/20 to-slate-600/10 border-slate-700/30';
  const iconColor = CATEGORY_ICON_COLORS[product.category] || 'text-slate-400';

  return (
    <div className="card card-hover overflow-hidden group">
      {/* Image / Icon Area */}
      <div className={`h-28 bg-gradient-to-br ${colorClass} flex items-center justify-center relative overflow-hidden`}>
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-300"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
              (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
            }}
          />
        ) : null}
        <div className={`${product.image_url ? 'hidden' : 'flex'} items-center justify-center`}>
          <Icon className={`w-10 h-10 ${iconColor} opacity-60 group-hover:opacity-90 transition-opacity`} />
        </div>
      </div>

      {/* Info */}
      <div className="p-3">
        <h3 className="text-xs font-semibold text-slate-100 truncate group-hover:text-primary-300 transition-colors" title={product.name}>
          {product.name}
        </h3>
        <p className="text-[10px] text-slate-500 mt-0.5">{product.brand}</p>
        <div className="flex items-center justify-between mt-2">
          <span className="text-sm font-bold text-accent-400">{formatPrice(product.price, product.symbol)}</span>
        </div>
        <span className="inline-block mt-1.5 text-[10px] font-medium text-primary-400 bg-primary-500/10 px-1.5 py-0.5 rounded">
          {product.reason_text}
        </span>
      </div>
    </div>
  );
}

interface CustomerViewProps {
  customer: CustomerFull;
  onLogout: () => void;
}

export default function CustomerView({ customer: initialCustomer, onLogout }: CustomerViewProps) {
  const [customer, setCustomer] = useState<CustomerFull>(initialCustomer);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loadingRecs, setLoadingRecs] = useState(true);
  const [recError, setRecError] = useState(false);
  const [currencies, setCurrencies] = useState<Record<string, string>>({});
  const [updatingCurrency, setUpdatingCurrency] = useState(false);

  useEffect(() => {
    apiClient.getCurrencies().then(setCurrencies).catch(() => {});
  }, []);

  const handleCurrencyChange = useCallback(async (newCurrency: string) => {
    if (newCurrency === customer.currency) return;
    setUpdatingCurrency(true);
    try {
      const updated = await apiClient.updateCustomerCurrency(customer.customer_id, newCurrency);
      setCustomer(updated);
      // Refresh recommendations with new currency
      setLoadingRecs(true);
      const data = await apiClient.getRecommendations(customer.customer_id);
      setRecommendations(data);
    } catch {
      // ignore
    } finally {
      setUpdatingCurrency(false);
    }
  }, [customer.customer_id, customer.currency]);

  useEffect(() => {
    let cancelled = false;
    setLoadingRecs(true);
    setRecError(false);

    apiClient.getRecommendations(customer.customer_id)
      .then((data) => {
        if (!cancelled) setRecommendations(data);
      })
      .catch(() => {
        if (!cancelled) setRecError(true);
      })
      .finally(() => {
        if (!cancelled) setLoadingRecs(false);
      });

    return () => { cancelled = true; };
  }, [customer.customer_id]);

  return (
    <div className="min-h-screen bg-surface">
      {/* Customer Header */}
      <header className="bg-slate-900/80 border-b border-slate-800 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-slate-100">
                Customer Portal
              </h1>
              <p className="text-xs text-slate-400">
                Welcome, {customer.name}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Currency Selector */}
            <div className="flex items-center gap-1.5 bg-slate-800/50 border border-slate-700/50 rounded-lg px-2.5 py-1.5">
              <DollarSign className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={customer.currency || 'USD'}
                onChange={(e) => handleCurrencyChange(e.target.value)}
                disabled={updatingCurrency}
                className="bg-transparent text-xs font-medium text-slate-200 border-none outline-none cursor-pointer appearance-none focus:ring-0 p-0"
              >
                {Object.entries(currencies).map(([code, symbol]) => (
                  <option key={code} value={code} className="bg-slate-800">
                    {code} ({symbol})
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={onLogout}
              className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg transition-all border border-slate-700/50 hover:border-slate-600/50"
            >
              <LogOut className="w-3.5 h-3.5" />
              Switch User
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-8">
        {/* Recommended for You */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Star className="w-5 h-5 text-accent-400" />
            <h2 className="text-lg font-semibold text-slate-100">Recommended for You</h2>
          </div>

          {loadingRecs && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="card overflow-hidden">
                  <div className="skeleton h-28 rounded-none" />
                  <div className="p-3 space-y-2">
                    <div className="skeleton h-3 w-3/4" />
                    <div className="skeleton h-2 w-1/2" />
                    <div className="skeleton h-4 w-1/3 mt-2" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loadingRecs && recError && (
            <div className="card p-6 text-center">
              <p className="text-sm text-slate-400">
                {customer.consent_status
                  ? 'Recommendations are not available yet. The model may need training.'
                  : 'Consent not granted. Personalised recommendations are unavailable.'}
              </p>
            </div>
          )}

          {!loadingRecs && !recError && recommendations.length === 0 && (
            <div className="card p-6 text-center">
              <p className="text-sm text-slate-400">No recommendations yet. Browse our catalogue below!</p>
            </div>
          )}

          {!loadingRecs && !recError && recommendations.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {recommendations.slice(0, 10).map((rec) => (
                <RecCard key={rec.product_id} product={rec} />
              ))}
            </div>
          )}
        </section>

        {/* All Products */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Package className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-semibold text-slate-100">All Products</h2>
          </div>
          <ProductSearch showAllOnMount customerId={customer.customer_id} />
        </section>
      </main>
    </div>
  );
}
