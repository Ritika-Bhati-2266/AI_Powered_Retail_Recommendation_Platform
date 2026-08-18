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

function DemoProductCard({ product, index, onClick, onAddToCart, onWishlist, isWishlisted = false }: { product: Product; index: number; onClick?: (product: Product) => void; onAddToCart?: (product: Product) => void; onWishlist?: (product: Product) => void; isWishlisted?: boolean; }) {
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
        <button
          onClick={(e) => { e.stopPropagation(); onWishlist?.(product); }}
          className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-8 h-8 rounded-full bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center hover:bg-rose-500/80" style={{ right: discount > 0 ? undefined : '12px', top: discount > 0 ? '48px' : '12px' }}>
          <Heart className={`w-4 h-4 ${isWishlisted ? 'fill-rose-500 text-rose-500' : 'text-zinc-300'}`} />
        </button>
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 translate-y-2 group-hover:translate-y-0">
          <button
            onClick={(e) => { e.stopPropagation(); onAddToCart?.(product); }}
            className="w-full flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur-md text-white text-xs font-semibold py-2.5 rounded-xl border border-white/20 transition-all">
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
          <button
            onClick={(e) => { e.stopPropagation(); onAddToCart?.(product); }}
            className="w-9 h-9 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 flex items-center justify-center transition-all group/add">
            <ShoppingCart className="w-4 h-4 text-purple-400 group-hover/add:text-purple-300 transition-colors" />
          </button>
        </div>
      </div>
    </div>
  );
}

function DemoProductDetailModal({ product, onClose, onAddToCart, onWishlist, isWishlisted = false }: { product: Product; onClose: () => void; onAddToCart?: (product: Product) => void; onWishlist?: (product: Product) => void; isWishlisted?: boolean; }) {
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
            {product.subcategory && (
              <span className="text-xs bg-zinc-800/50 text-zinc-400 px-2.5 py-1 rounded-full border border-zinc-700/50">
                {product.subcategory}
              </span>
            )}
            <StarRating rating={rating} />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={() => { onAddToCart?.(product); onClose(); }}
              className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 text-white text-sm font-semibold py-3 rounded-xl transition-all"
            >
              <ShoppingCart className="w-4 h-4" />
              Add to Cart
            </button>
            <button
              onClick={() => { onWishlist?.(product); }}
              className="flex items-center justify-center gap-2 bg-zinc-800/50 hover:bg-zinc-700/50 text-zinc-300 text-sm font-semibold py-3 px-4 rounded-xl border border-zinc-700/50 transition-all"
            >
              <Heart className={`w-4 h-4 ${isWishlisted ? 'fill-rose-500 text-rose-500' : ''}`} />
              {isWishlisted ? 'Wishlisted' : 'Wishlist'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DemoCartPanel({ items, onClose, onRemove }: { items: Map<string, { product: Product; quantity: number }>; onClose: () => void; onRemove: (productId: string) => void; }) {
  const itemArray = Array.from(items.values());
  const total = itemArray.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-zinc-900 border-l border-zinc-800 h-full flex flex-col shadow-2xl shadow-purple-600/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-purple-400" />
            Demo Cart ({itemArray.reduce((c, i) => c + i.quantity, 0)})
          </h2>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-zinc-800/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        <div className="px-5 py-3 bg-amber-500/10 border-b border-amber-500/20">
          <p className="text-xs text-amber-300 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 flex-shrink-0" />
            This is a demo — your cart is only kept in this browser session. Sign up to save it permanently.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {itemArray.length === 0 && (
            <div className="text-center py-12">
              <ShoppingCart className="w-16 h-16 text-zinc-700 mx-auto mb-3" />
              <p className="text-zinc-500 text-sm">Your cart is empty</p>
            </div>
          )}
          {itemArray.map(({ product, quantity }) => (
            <div key={product.product_id} className="flex items-center gap-3 bg-zinc-800/30 rounded-xl p-3 border border-zinc-800/50">
              <div className="w-14 h-14 rounded-lg bg-zinc-800 overflow-hidden flex-shrink-0">
                {product.image_url && (
                  <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-200 truncate">{product.name}</p>
                <p className="text-xs text-zinc-500">{formatPrice(product.price, product.symbol)} × {quantity}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-sm font-semibold text-purple-400">{formatPrice(product.price * quantity, product.symbol)}</p>
                <button onClick={() => onRemove(product.product_id)} className="text-xs text-zinc-500 hover:text-rose-400 transition-colors mt-0.5">Remove</button>
              </div>
            </div>
          ))}
        </div>

        {itemArray.length > 0 && (
          <div className="border-t border-zinc-800 px-5 py-4 space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Total</span>
              <span className="text-lg font-bold text-purple-400">{formatPrice(total, itemArray[0]?.product.symbol)}</span>
            </div>
            <p className="text-[11px] text-zinc-500 text-center">
              Checkout is disabled in demo mode. Sign up as a customer to place real orders.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function DemoWishlistPanel({ items, onClose, onRemove, onView }: { items: Product[]; onClose: () => void; onRemove: (productId: string) => void; onView: (product: Product) => void; }) {
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-zinc-900 border-l border-zinc-800 h-full flex flex-col shadow-2xl shadow-purple-600/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
            <Heart className="w-5 h-5 text-rose-400" />
            Demo Wishlist ({items.length})
          </h2>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-zinc-800/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all"
          >
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        <div className="px-5 py-3 bg-amber-500/10 border-b border-amber-500/20">
          <p className="text-xs text-amber-300 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 flex-shrink-0" />
            This is a demo — your wishlist is only kept in this browser session. Sign up to save it permanently.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {items.length === 0 && (
            <div className="text-center py-12">
              <Heart className="w-16 h-16 text-zinc-700 mx-auto mb-3" />
              <p className="text-zinc-500 text-sm">Your wishlist is empty</p>
              <p className="text-zinc-600 text-xs mt-1">Tap the heart on any product to save it here.</p>
            </div>
          )}
          {items.map((product) => (
            <div key={product.product_id} className="flex items-center gap-3 bg-zinc-800/30 rounded-xl p-3 border border-zinc-800/50">
              <div
                className="w-14 h-14 rounded-lg bg-zinc-800 overflow-hidden flex-shrink-0 cursor-pointer"
                onClick={() => onView(product)}
              >
                {product.image_url && (
                  <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
                )}
              </div>
              <div
                className="flex-1 min-w-0 cursor-pointer"
                onClick={() => onView(product)}
              >
                <p className="text-sm font-medium text-zinc-200 truncate">{product.name}</p>
                <p className="text-xs text-zinc-500 mt-0.5">{formatPrice(product.price, product.symbol)}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <button
                  onClick={() => onRemove(product.product_id)}
                  className="flex items-center gap-1 text-xs text-zinc-500 hover:text-rose-400 transition-colors"
                >
                  <X className="w-3 h-3" /> Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Toast({ toast }: { toast: { message: string; type: string } | null }) {
  if (!toast) return null;
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[60] animate-fade-in-up">
      <div className="bg-zinc-800/95 backdrop-blur-md border border-zinc-700/50 rounded-xl px-5 py-3 shadow-xl shadow-purple-600/10 flex items-center gap-2.5">
        <div className={`w-2 h-2 rounded-full ${toast.type === 'success' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
        <span className="text-sm text-zinc-200">{toast.message}</span>
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

  const [cartItems, setCartItems] = useState<Map<string, { product: Product; quantity: number }>>(new Map());
  const [wishlistItems, setWishlistItems] = useState<Set<string>>(new Set());
  const [wishlistProducts, setWishlistProducts] = useState<Product[]>([]);
  const [showCart, setShowCart] = useState(false);
  const [showWishlist, setShowWishlist] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: string } | null>(null);

  const showToast = (message: string, type: string = 'success') => {
    setToast({ message, type });
    window.setTimeout(() => setToast(null), 2500);
  };

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

  const cartCount = useMemo(() => {
    let count = 0;
    cartItems.forEach((item) => { count += item.quantity; });
    return count;
  }, [cartItems]);

  const handleAddToCart = (product: Product) => {
    setCartItems((prev) => {
      const next = new Map(prev);
      const existing = next.get(product.product_id);
      if (existing) {
        next.set(product.product_id, { ...existing, quantity: existing.quantity + 1 });
      } else {
        next.set(product.product_id, { product, quantity: 1 });
      }
      return next;
    });
    showToast(`${product.name.substring(0, 30)}… added to cart`);
  };

  const handleRemoveFromCart = (productId: string) => {
    setCartItems((prev) => {
      const next = new Map(prev);
      const existing = next.get(productId);
      if (existing && existing.quantity > 1) {
        next.set(productId, { ...existing, quantity: existing.quantity - 1 });
      } else {
        next.delete(productId);
      }
      return next;
    });
  };

  const handleWishlist = (product: Product) => {
    setWishlistItems((prev) => {
      const next = new Set(prev);
      if (next.has(product.product_id)) {
        next.delete(product.product_id);
        showToast(`${product.name.substring(0, 30)}… removed from wishlist`);
      } else {
        next.add(product.product_id);
        showToast(`${product.name.substring(0, 30)}… added to wishlist`);
      }
      return next;
    });
    setWishlistProducts((prev) => {
      if (!wishlistItems.has(product.product_id)) {
        return prev.some((p) => p.product_id === product.product_id)
          ? prev
          : [product, ...prev];
      }
      return prev.filter((p) => p.product_id !== product.product_id);
    });
  };

  const handleRemoveWishlist = (productId: string) => {
    const p = wishlistProducts.find((item) => item.product_id === productId);
    if (p) handleWishlist(p);
  };

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
            <button onClick={() => setShowCart(true)} title="Your Cart" className="relative w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <ShoppingCart className="w-4 h-4 text-zinc-300" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 bg-gradient-to-br from-purple-600 to-pink-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center shadow-lg px-1">{cartCount}</span>
              )}
            </button>
            <button onClick={() => setShowWishlist(true)} title="Your Wishlist" className="relative w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <Heart className="w-4 h-4 text-rose-400" />
              {wishlistItems.size > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 bg-rose-600 rounded-full text-[9px] font-bold text-white flex items-center justify-center shadow-lg px-1">{wishlistItems.size}</span>
              )}
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
          <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3 mb-6">
            <Clock className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <p className="text-xs text-amber-300">
              <span className="font-semibold">This is a demo.</span> Items you add to your cart or wishlist are only stored in this browser session — sign up to save your cart permanently.
            </p>
          </div>

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
                <DemoProductCard
                  key={product.product_id}
                  product={product}
                  index={i}
                  onClick={setSelectedDemoProduct}
                  onAddToCart={handleAddToCart}
                  onWishlist={handleWishlist}
                  isWishlisted={wishlistItems.has(product.product_id)}
                />
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
          onAddToCart={handleAddToCart}
          onWishlist={handleWishlist}
          isWishlisted={wishlistItems.has(selectedDemoProduct.product_id)}
        />
      )}

      {showCart && (
        <DemoCartPanel
          items={cartItems}
          onClose={() => setShowCart(false)}
          onRemove={handleRemoveFromCart}
        />
      )}

      {showWishlist && (
        <DemoWishlistPanel
          items={wishlistProducts}
          onClose={() => setShowWishlist(false)}
          onRemove={handleRemoveWishlist}
          onView={setSelectedDemoProduct}
        />
      )}

      <Toast toast={toast} />
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