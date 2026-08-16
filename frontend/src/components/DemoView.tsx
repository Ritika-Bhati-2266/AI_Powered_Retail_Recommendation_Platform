import { useState, useEffect, useMemo } from 'react';
import {
  Sparkles, ShoppingBag, Search, ShoppingCart, User, Star,
  Package, Smartphone, Shirt, Sofa, BookOpen, Dumbbell,
  Gamepad2, Apple, Heart, Plus, ArrowLeft, RefreshCw, Clock,
  LogOut, X, Tag, Loader2,
} from 'lucide-react';
import { formatPrice } from '../utils/formatPrice';
import { apiClient } from '../api/client';
import type { Product } from '../types';

const CATEGORY_ICONS: Record<string, typeof Smartphone> = {
  Electronics: Smartphone,
  Clothing: Shirt,
  'Home & Kitchen': Sofa,
  Books: BookOpen,
  'Sports & Outdoors': Dumbbell,
  'Beauty & Personal Care': Sparkles,
  'Toys & Games': Gamepad2,
  'Grocery & Gourmet': Apple,
  Automotive: Smartphone,
  'Baby & Kids': Shirt,
  'Health & Wellness': Sparkles,
  'Music & Media': BookOpen,
  'Office & Stationery': Package,
  'Pet Supplies': Package,
};

const CATEGORY_COLORS: Record<string, string> = {
  Electronics: 'from-cyan-500/20 to-cyan-600/10 border-cyan-700/30',
  Clothing: 'from-pink-500/20 to-pink-600/10 border-pink-700/30',
  'Home & Kitchen': 'from-amber-500/20 to-amber-600/10 border-amber-700/30',
  Books: 'from-emerald-500/20 to-emerald-600/10 border-emerald-700/30',
  'Sports & Outdoors': 'from-blue-500/20 to-blue-600/10 border-blue-700/30',
  'Beauty & Personal Care': 'from-purple-500/20 to-purple-600/10 border-purple-700/30',
  'Toys & Games': 'from-orange-500/20 to-orange-600/10 border-orange-700/30',
  'Grocery & Gourmet': 'from-lime-500/20 to-lime-600/10 border-lime-700/30',
  Automotive: 'from-cyan-500/20 to-cyan-600/10 border-cyan-700/30',
  'Baby & Kids': 'from-pink-500/20 to-pink-600/10 border-pink-700/30',
  'Health & Wellness': 'from-purple-500/20 to-purple-600/10 border-purple-700/30',
  'Music & Media': 'from-emerald-500/20 to-emerald-600/10 border-emerald-700/30',
  'Office & Stationery': 'from-zinc-500/20 to-zinc-600/10 border-zinc-700/30',
  'Pet Supplies': 'from-amber-500/20 to-amber-600/10 border-amber-700/30',
};

const CATEGORY_ICON_COLORS: Record<string, string> = {
  Electronics: 'text-cyan-400',
  Clothing: 'text-pink-400',
  'Home & Kitchen': 'text-amber-400',
  Books: 'text-emerald-400',
  'Sports & Outdoors': 'text-blue-400',
  'Beauty & Personal Care': 'text-purple-400',
  'Toys & Games': 'text-orange-400',
  'Grocery & Gourmet': 'text-lime-400',
  Automotive: 'text-cyan-400',
  'Baby & Kids': 'text-pink-400',
  'Health & Wellness': 'text-purple-400',
  'Music & Media': 'text-emerald-400',
  'Office & Stationery': 'text-zinc-400',
  'Pet Supplies': 'text-amber-400',
};

function getCategoryIcon(category: string) {
  return CATEGORY_ICONS[category] || Package;
}

function StarRating({ rating }: { rating: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: full }, (_, i) => <Star key={`f${i}`} className="w-3 h-3 fill-amber-400 text-amber-400" />)}
      {half && <Star className="w-3 h-3 fill-amber-400 text-amber-400" />}
      {Array.from({ length: empty }, (_, i) => <Star key={`e${i}`} className="w-3 h-3 text-zinc-600" />)}
      <span className="text-xs text-zinc-400 ml-1">{rating}</span>
    </div>
  );
}

function DemoProductCard({ product, index, onClick }: { product: Product; index: number; onClick?: (product: Product) => void }) {
  const Icon = getCategoryIcon(product.category);
  const colorClass = CATEGORY_COLORS[product.category] || 'from-zinc-500/20 to-zinc-600/10 border-zinc-700/30';
  const iconColor = CATEGORY_ICON_COLORS[product.category] || 'text-zinc-400';
  const rating = product.rating ?? 0;
  const discount = product.discount_percent ?? 0;
  const originalPrice = product.original_price ?? product.price;

  return (
    <div
      onClick={() => onClick?.(product)}
      className="group bg-zinc-900/50 border border-zinc-800/50 rounded-2xl overflow-hidden hover:border-zinc-700/50 transition-all duration-300 hover:shadow-xl hover:shadow-purple-600/5 hover:-translate-y-0.5 cursor-pointer"
      style={{ animationDelay: `${index * 80}ms` }}
    >
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
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 translate-y-2 group-hover:translate-y-0">
          <button className="w-full flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur-md text-white text-xs font-semibold py-2.5 rounded-xl border border-white/20 transition-all">
            <Plus className="w-3.5 h-3.5" /> Add to Cart
          </button>
        </div>
      </div>
      <div className="p-4 space-y-2.5">
        <h3 className="text-sm font-semibold text-zinc-100 truncate group-hover:text-purple-300 transition-colors">{product.name}</h3>
        <p className="text-xs text-zinc-500">{product.brand}</p>
        <StarRating rating={rating} />
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-purple-400">{formatPrice(product.price, product.symbol)}</span>
            {originalPrice > product.price && <span className="text-xs text-zinc-600 line-through">{formatPrice(originalPrice, product.symbol)}</span>}
          </div>
          <button className="w-9 h-9 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 flex items-center justify-center transition-all group/add">
            <ShoppingCart className="w-4 h-4 text-purple-400 group-hover/add:text-purple-300 transition-colors" />
          </button>
        </div>
      </div>
    </div>
  );
}

function DemoProductDetailModal({ product, onClose }: { product: Product; onClose: () => void }) {
  const Icon = getCategoryIcon(product.category);
  const colorClass = CATEGORY_COLORS[product.category] || 'from-zinc-500/20 to-zinc-600/10 border-zinc-700/30';
  const iconColor = CATEGORY_ICON_COLORS[product.category] || 'text-zinc-400';
  const rating = product.rating ?? 0;
  const discount = product.discount_percent ?? 0;
  const originalPrice = product.original_price ?? product.price;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl shadow-purple-600/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative">
          <div className={`aspect-[16/9] bg-gradient-to-br ${colorClass} relative overflow-hidden rounded-t-2xl`}>
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                  (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                }}
              />
            ) : null}
            <div className={`${product.image_url ? 'hidden' : 'flex'} absolute inset-0 items-center justify-center`}>
              <Icon className={`w-20 h-20 ${iconColor} opacity-30`} />
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          </div>
          <button
            onClick={onClose}
            className="absolute top-3 right-3 w-8 h-8 rounded-full bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center hover:bg-zinc-700/80 transition-all"
          >
            <X className="w-4 h-4 text-zinc-300" />
          </button>
          {discount > 0 && (
            <span className="absolute top-3 left-3 bg-gradient-to-r from-rose-600 to-pink-600 text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg shadow-rose-600/30 flex items-center gap-1">
              <Tag className="w-3 h-3" /> {discount}% OFF
            </span>
          )}
        </div>

        <div className="p-6 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <h2 className="text-xl font-bold text-zinc-100">{product.name}</h2>
              <p className="text-sm text-zinc-500">{product.brand}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-purple-400">{formatPrice(product.price, product.symbol)}</p>
              {originalPrice > product.price && (
                <p className="text-sm text-zinc-600 line-through">{formatPrice(originalPrice, product.symbol)}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs bg-zinc-800 text-zinc-300 px-2.5 py-1 rounded-full border border-zinc-700/50">
              {product.category}
            </span>
            <StarRating rating={rating} />
          </div>
        </div>
      </div>
    </div>
  );
}

interface DemoViewProps {
  onBack: () => void;
}

const CATALOG_DISPLAY_LIMIT = 60;

export default function DemoView({ onBack }: DemoViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDemoProduct, setSelectedDemoProduct] = useState<Product | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const catalog = await apiClient.searchProducts('');
        if (!cancelled) setProducts(catalog);
      } catch {
        if (!cancelled) setError('Could not load the product catalog. Please try again.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return products.slice(0, CATALOG_DISPLAY_LIMIT);
    const q = searchQuery.toLowerCase();
    return products.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q) ||
      p.brand.toLowerCase().includes(q)
    );
  }, [searchQuery, products]);

  return (
    <div className="min-h-screen bg-black">
      <header className="bg-zinc-900/80 border-b border-zinc-800 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={onBack} className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-all">
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
              <ShoppingBag className="w-4 h-4 text-white" />
            </div>
            <span className="hidden sm:block text-lg font-bold text-purple-400">PersonalShop</span>
          </div>

          <div className="hidden md:flex flex-1 max-w-md mx-6">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search the catalog..."
                className="w-full bg-zinc-800/50 text-zinc-100 placeholder-zinc-500 border border-zinc-700/50 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <div className="hidden sm:flex items-center gap-1.5 bg-zinc-800/50 border border-zinc-700/50 rounded-xl px-2.5 py-1.5">
              <DollarSign className="w-3.5 h-3.5 text-zinc-400" />
              <span className="text-xs font-medium text-zinc-200">USD</span>
            </div>
            <button className="relative w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <ShoppingCart className="w-4 h-4 text-zinc-300" />
            </button>
            <div className="flex items-center gap-2 pl-2 border-l border-zinc-800">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-medium text-zinc-200">Demo Guest</p>
              </div>
              <button onClick={onBack} className="ml-1 p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-all" title="Exit Demo">
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="bg-black">
        <div className="max-w-7xl mx-auto px-6 pt-12 pb-12 md:pb-16 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            LIVE DEMO — NO SIGNUP NEEDED
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight leading-tight mb-4">
            Explore{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500">
              Personalized
            </span>{' '}
            Shopping
          </h1>
          <p className="text-base text-zinc-400 max-w-lg mx-auto">
            Browse the live catalog — {loading ? 'loading…' : `${products.length} products`} — no signup needed.
          </p>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-10 pb-16">
        <section>
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <Star className="w-4 h-4 text-purple-400" />
            </div>
            <h2 className="text-xl font-bold text-zinc-100">
              {searchQuery.trim() ? `Results for "${searchQuery}"` : 'Browse the Catalog'}
            </h2>
            <button
              onClick={() => setSearchQuery('')}
              className="ml-1 p-1.5 rounded-lg text-zinc-500 hover:text-purple-400 hover:bg-zinc-800/50 transition-all"
              title="Clear search"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            {!searchQuery.trim() && products.length > CATALOG_DISPLAY_LIMIT && (
              <span className="text-xs text-zinc-500">Showing {CATALOG_DISPLAY_LIMIT} of {products.length}</span>
            )}
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-purple-400" />
              <p className="text-sm">Loading product catalog…</p>
            </div>
          ) : error ? (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center space-y-3">
              <p className="text-sm text-zinc-400">{error}</p>
              <button
                onClick={() => {
                  setLoading(true);
                  setError(null);
                  apiClient.searchProducts('').then(setProducts).catch(() => setError('Could not load the product catalog. Please try again.')).finally(() => setLoading(false));
                }}
                className="px-4 py-2 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 text-sm font-medium transition-all"
              >
                Retry
              </button>
            </div>
          ) : filtered.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {filtered.map((product, i) => (
                <DemoProductCard key={product.product_id} product={product} index={i} onClick={setSelectedDemoProduct} />
              ))}
            </div>
          ) : (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
              <p className="text-sm text-zinc-400">No matching products found. Try a different search term.</p>
            </div>
          )}
        </section>
      </main>

      {selectedDemoProduct && (
        <DemoProductDetailModal
          product={selectedDemoProduct}
          onClose={() => setSelectedDemoProduct(null)}
        />
      )}
    </div>
  );
}

function DollarSign(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  );
}