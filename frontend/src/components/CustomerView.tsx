import { useState, useEffect, useCallback, useMemo } from 'react';
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
  DollarSign,
  Clock,
  ShoppingBag,
  Search,
  ShoppingCart,
  User,
  RefreshCw,
  Heart,
  Plus,
} from 'lucide-react';
import { apiClient } from '../api/client';
import ProductSearch from './ProductSearch';
import { formatPrice } from '../utils/formatPrice';
import type { CustomerFull, Recommendation, Product } from '../types';

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

function hashId(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function useProductEnhancements(product: Product | Recommendation) {
  return useMemo(() => {
    const h = hashId(product.product_id);
    const rating = product.rating ?? (3.5 + (h % 15) / 10);
    const hasDiscount = (h % 5) !== 0;
    const discount = product.discount_percent ?? (hasDiscount ? 10 + (h % 25) : 0);
    const originalPrice = product.original_price ?? (discount > 0 ? Math.round(product.price / (1 - discount / 100) * 100) / 100 : product.price);
    return { rating: Math.min(5, Math.round(rating * 10) / 10), discount, originalPrice };
  }, [product]);
}

function StarRating({ rating }: { rating: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: full }, (_, i) => (
        <Star key={`full-${i}`} className="w-3 h-3 fill-amber-400 text-amber-400" />
      ))}
      {half && <Star className="w-3 h-3 fill-amber-400 text-amber-400" />}
      {Array.from({ length: empty }, (_, i) => (
        <Star key={`empty-${i}`} className="w-3 h-3 text-zinc-600" />
      ))}
      <span className="text-xs text-zinc-400 ml-1">{rating}</span>
    </div>
  );
}

function PremiumProductCard({ product, showAddToCart = true }: { product: Product | Recommendation; showAddToCart?: boolean }) {
  const Icon = getCategoryIcon(product.category);
  const colorClass = CATEGORY_COLORS[product.category] || 'from-zinc-500/20 to-zinc-600/10 border-zinc-700/30';
  const iconColor = CATEGORY_ICON_COLORS[product.category] || 'text-zinc-400';
  const { rating, discount, originalPrice } = useProductEnhancements(product);

  return (
    <div className="group bg-zinc-900/50 border border-zinc-800/50 rounded-2xl overflow-hidden hover:border-zinc-700/50 transition-all duration-300 hover:shadow-xl hover:shadow-purple-600/5 hover:-translate-y-0.5">
        <div className={`relative aspect-[4/3] bg-gradient-to-br ${colorClass} overflow-hidden`}>
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
              (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
            }}
          />
        ) : null}
        <div className={`${product.image_url ? 'hidden' : 'flex'} absolute inset-0 items-center justify-center`}>
          <Icon className={`w-14 h-14 ${iconColor} opacity-50`} />
        </div>

        <span className="absolute top-3 left-3 bg-zinc-900/80 backdrop-blur-sm text-[10px] font-medium text-zinc-300 px-2.5 py-1 rounded-full border border-zinc-700/50">
          {product.category}
        </span>

        {discount > 0 && (
          <span className="absolute top-3 right-3 bg-gradient-to-r from-rose-600 to-pink-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-full shadow-lg shadow-rose-600/30">
            {discount}% OFF
          </span>
        )}

        <button className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-8 h-8 rounded-full bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center hover:bg-rose-500/80" style={{ right: discount > 0 ? undefined : '12px', top: discount > 0 ? '48px' : '12px' }}>
          <Heart className="w-4 h-4 text-zinc-300" />
        </button>

        {showAddToCart && (
          <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 translate-y-2 group-hover:translate-y-0">
            <button className="w-full flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur-md text-white text-xs font-semibold py-2.5 rounded-xl border border-white/20 transition-all">
              <Plus className="w-3.5 h-3.5" />
              Add to Cart
            </button>
          </div>
        )}
      </div>

      <div className="p-4 space-y-2.5">
        <h3 className="text-sm font-semibold text-zinc-100 truncate group-hover:text-purple-300 transition-colors" title={product.name}>
          {product.name}
        </h3>
        <p className="text-xs text-zinc-500">{product.brand}</p>
        <StarRating rating={rating} />
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-purple-400">{formatPrice(product.price, product.symbol)}</span>
            {originalPrice > product.price && (
              <span className="text-xs text-zinc-600 line-through">{formatPrice(originalPrice, product.symbol)}</span>
            )}
          </div>
          <button className="w-9 h-9 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 flex items-center justify-center transition-all group/add">
            <ShoppingCart className="w-4 h-4 text-purple-400 group-hover/add:text-purple-300 transition-colors" />
          </button>
        </div>
      </div>
    </div>
  );
}

function SkeletonGrid({ count = 5 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl overflow-hidden">
          <div className="skeleton aspect-[4/3] rounded-none" />
          <div className="p-4 space-y-2.5">
            <div className="skeleton h-4 w-3/4" />
            <div className="skeleton h-3 w-1/2" />
            <div className="skeleton h-3 w-1/3" />
            <div className="skeleton h-5 w-1/3" />
          </div>
        </div>
      ))}
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

  const [recentlyViewed, setRecentlyViewed] = useState<Product[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(true);

  const [continueShopping, setContinueShopping] = useState<Product[]>([]);
  const [loadingContinue, setLoadingContinue] = useState(true);

  useEffect(() => {
    apiClient.getCurrencies().then(setCurrencies).catch(() => {});
  }, []);

  const handleCurrencyChange = useCallback(async (newCurrency: string) => {
    if (newCurrency === customer.currency) return;
    setUpdatingCurrency(true);
    try {
      const updated = await apiClient.updateCustomerCurrency(customer.customer_id, newCurrency);
      setCustomer(updated);
      setLoadingRecs(true);
      const data = await apiClient.getRecommendations(customer.customer_id);
      setRecommendations(data);
    } catch {
      // ignore
    } finally {
      setUpdatingCurrency(false);
    }
  }, [customer.customer_id, customer.currency]);

  const fetchRecommendations = useCallback(() => {
    let cancelled = false;
    setLoadingRecs(true);
    setRecError(false);
    apiClient.getRecommendations(customer.customer_id)
      .then((data) => { if (!cancelled) setRecommendations(data); })
      .catch(() => { if (!cancelled) setRecError(true); })
      .finally(() => { if (!cancelled) setLoadingRecs(false); });
    return () => { cancelled = true; };
  }, [customer.customer_id]);

  useEffect(fetchRecommendations, [fetchRecommendations]);

  useEffect(() => {
    let cancelled = false;
    setLoadingRecent(true);
    apiClient.getRecentlyViewed(customer.customer_id)
      .then((data) => { if (!cancelled) setRecentlyViewed(data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingRecent(false); });
    return () => { cancelled = true; };
  }, [customer.customer_id]);

  useEffect(() => {
    let cancelled = false;
    setLoadingContinue(true);
    apiClient.getContinueShopping(customer.customer_id)
      .then((data) => { if (!cancelled) setContinueShopping(data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingContinue(false); });
    return () => { cancelled = true; };
  }, [customer.customer_id]);

  return (
    <div className="min-h-screen bg-black">
      <header className="bg-zinc-900/80 border-b border-zinc-800 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
              <ShoppingBag className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-purple-400">PersonalShop</span>
          </div>

          <div className="hidden md:flex flex-1 max-w-md mx-6">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Search products..."
                className="w-full bg-zinc-800/50 text-zinc-100 placeholder-zinc-500 border border-zinc-700/50 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="relative w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <ShoppingCart className="w-4 h-4 text-zinc-300" />
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-br from-purple-600 to-pink-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center shadow-lg">3</span>
            </button>

            <div className="flex items-center gap-1.5 bg-zinc-800/50 border border-zinc-700/50 rounded-xl px-2.5 py-1.5">
              <DollarSign className="w-3.5 h-3.5 text-zinc-400" />
              <select
                value={customer.currency || 'USD'}
                onChange={(e) => handleCurrencyChange(e.target.value)}
                disabled={updatingCurrency}
                className="bg-transparent text-xs font-medium text-zinc-200 border-none outline-none cursor-pointer appearance-none focus:ring-0 p-0"
              >
                {Object.entries(currencies).map(([code, symbol]) => (
                  <option key={code} value={code} className="bg-zinc-900">
                    {code} ({symbol})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 pl-2 border-l border-zinc-800">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-medium text-zinc-200">{customer.name}</p>
              </div>
              <button
                onClick={onLogout}
                className="ml-1 p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-all"
                title="Switch User"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="bg-black">

        <div className="max-w-7xl mx-auto px-6 py-16 md:py-24 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            Welcome back, {customer.name}
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight leading-tight mb-4">
            The Store That{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500">
              Learns You
            </span>
          </h1>
          <p className="text-base text-zinc-400 max-w-lg mx-auto">
            Your store adapts to every click. Discover products curated just for you.
          </p>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-10">
        <section>
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-purple-500/10 flex items-center justify-center">
                  <Star className="w-4 h-4 text-purple-400" />
                </div>
                <h2 className="text-xl font-bold text-zinc-100">Recommended for You</h2>
                <button
                  onClick={fetchRecommendations}
                  className="ml-1 p-1.5 rounded-lg text-zinc-500 hover:text-purple-400 hover:bg-zinc-800/50 transition-all"
                  title="Refresh recommendations"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-zinc-500 mt-1">Dynamic recommendations updating as you browse</p>
            </div>
          </div>

          {loadingRecs && <SkeletonGrid count={5} />}

          {!loadingRecs && recError && (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
              <p className="text-sm text-zinc-400">
                {customer.consent_status
                  ? 'Recommendations are not available yet. The model may need training.'
                  : 'Consent not granted. Personalised recommendations are unavailable.'}
              </p>
            </div>
          )}

          {!loadingRecs && !recError && recommendations.length === 0 && (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
              <p className="text-sm text-zinc-400">No recommendations yet. Browse our catalogue below!</p>
            </div>
          )}

          {!loadingRecs && !recError && recommendations.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {recommendations.slice(0, 10).map((rec) => (
                <PremiumProductCard key={rec.product_id} product={rec} showAddToCart={false} />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/10 flex items-center justify-center">
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <h2 className="text-xl font-bold text-zinc-100">Recently Viewed</h2>
          </div>

          {loadingRecent && <SkeletonGrid count={5} />}

          {!loadingRecent && recentlyViewed.length === 0 && (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
              <p className="text-sm text-zinc-400">No recently viewed products yet. Start browsing!</p>
            </div>
          )}

          {!loadingRecent && recentlyViewed.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {recentlyViewed.map((product) => (
                <PremiumProductCard key={product.product_id} product={product} />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 flex items-center justify-center">
              <ShoppingBag className="w-4 h-4 text-amber-400" />
            </div>
            <h2 className="text-xl font-bold text-zinc-100">Continue Shopping</h2>
          </div>

          {loadingContinue && <SkeletonGrid count={5} />}

          {!loadingContinue && continueShopping.length === 0 && (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
              <p className="text-sm text-zinc-400">No items in your cart. Add something to get started!</p>
            </div>
          )}

          {!loadingContinue && continueShopping.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {continueShopping.map((product) => (
                <PremiumProductCard key={product.product_id} product={product} />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <Package className="w-4 h-4 text-purple-400" />
            </div>
            <h2 className="text-xl font-bold text-zinc-100">All Products</h2>
          </div>
          <ProductSearch showAllOnMount customerId={customer.customer_id} />
        </section>
      </main>
    </div>
  );
}
