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
  X,
  Tag,
  Eye,
  Receipt,
  ShieldCheck,
  ShieldX,
  Download,
  Info,
} from 'lucide-react';
import { apiClient } from '../api/client';
import ProductSearch from './ProductSearch';
import PrivacyModal from './PrivacyModal';
import { formatPrice } from '../utils/formatPrice';
import type { CustomerFull, Recommendation, Product, Order } from '../types';

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

function PremiumProductCard({ product, showAddToCart = true, onAddToCart, onWishlist, onClick, isWishlisted = false }: { product: Product | Recommendation; showAddToCart?: boolean; onAddToCart?: (product: Product | Recommendation) => void; onWishlist?: (product: Product | Recommendation) => void; onClick?: (product: Product | Recommendation) => void; isWishlisted?: boolean; }) {
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
          className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-all duration-200 w-8 h-8 rounded-full bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center hover:bg-rose-500/80" style={{ right: discount > 0 ? undefined : '12px', top: discount > 0 ? '48px' : '12px' }}>
          <Heart className={`w-4 h-4 ${isWishlisted ? 'fill-rose-500 text-rose-500' : 'text-zinc-300'}`} />
        </button>

        {showAddToCart && (
          <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 translate-y-2 group-hover:translate-y-0">
            <button
              onClick={(e) => { e.stopPropagation(); onAddToCart?.(product); }}
              className="w-full flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur-md text-white text-xs font-semibold py-2.5 rounded-xl border border-white/20 transition-all">
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

function ProductDetailModal({ product, onClose, onAddToCart, onWishlist, isWishlisted = false }: { product: Product | Recommendation; onClose: () => void; onAddToCart?: (product: Product | Recommendation) => void; onWishlist?: (product: Product | Recommendation) => void; isWishlisted?: boolean; }) {
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

function CartPanel({ items, onClose, onRemove, onCheckout, submitting = false }: { items: Map<string, { product: Product | Recommendation; quantity: number }>; onClose: () => void; onRemove: (productId: string) => void; onCheckout: () => void; submitting?: boolean; }) {
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
            Your Cart ({itemArray.reduce((c, i) => c + i.quantity, 0)})
          </h2>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-zinc-800/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
            <X className="w-4 h-4 text-zinc-400" />
          </button>
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
            <button
              onClick={onCheckout}
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 text-white text-sm font-semibold py-3 rounded-xl transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {submitting ? 'Placing order...' : `Checkout (${itemArray.reduce((c, i) => c + i.quantity, 0)} items)`}
            </button>
          </div>
        )}
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

function OrderHistoryModal({ orders, symbolFor, onClose, loading, error }: { orders: Order[]; symbolFor: (currency: string) => string; onClose: () => void; loading: boolean; error: boolean; }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl shadow-purple-600/10" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
            <Receipt className="w-5 h-5 text-purple-400" />
            Order History
          </h2>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-zinc-800/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {loading && <p className="text-sm text-zinc-500 py-8 text-center">Loading your orders...</p>}
          {!loading && error && <p className="text-sm text-rose-400 py-8 text-center">Could not load order history.</p>}
          {!loading && !error && orders.length === 0 && (
            <div className="text-center py-12">
              <Receipt className="w-14 h-14 text-zinc-700 mx-auto mb-3" />
              <p className="text-zinc-500 text-sm">No orders yet. Place items in your cart and check out!</p>
            </div>
          )}
          {orders.map((order) => (
            <div key={order.order_id} className="bg-zinc-800/30 border border-zinc-800/50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-semibold text-zinc-200">Order #{order.order_id.slice(0, 8)}</p>
                  <p className="text-xs text-zinc-500">{new Date(order.created_at).toLocaleString()}</p>
                </div>
                <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase ${order.status === 'placed' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-zinc-700/40 text-zinc-300'}`}>{order.status}</span>
              </div>
              <div className="space-y-1.5 mb-3">
                {order.items.map((item) => (
                  <div key={item.order_item_id} className="flex items-center justify-between text-sm">
                    <span className="text-zinc-300 truncate pr-3">{item.product_name_snapshot} × {item.quantity}</span>
                    <span className="text-zinc-400 flex-shrink-0">{formatPrice(item.subtotal, symbolFor(order.currency))}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-zinc-800/60">
                <span className="text-sm text-zinc-400">Total</span>
                <span className="text-base font-bold text-purple-400">{formatPrice(order.total_amount, symbolFor(order.currency))}</span>
              </div>
            </div>
          ))}
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
  const [navbarSearch, setNavbarSearch] = useState('');

  const [selectedProduct, setSelectedProduct] = useState<Product | Recommendation | null>(null);
  const [cartItems, setCartItems] = useState<Map<string, { product: Product | Recommendation; quantity: number }>>(new Map());
  const [wishlistItems, setWishlistItems] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ message: string; type: string } | null>(null);
  const [showCart, setShowCart] = useState(false);
  const [submittingOrder, setSubmittingOrder] = useState(false);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [orderError, setOrderError] = useState(false);
  const [showOrders, setShowOrders] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [updatingConsent, setUpdatingConsent] = useState(false);
  const [exportingData, setExportingData] = useState(false);

  const sessionId = useMemo(() => `session_${crypto.randomUUID()}`, []);

  const showToast = useCallback((message: string, type: string = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 2500);
  }, []);

  const cartCount = useMemo(() => {
    let count = 0;
    cartItems.forEach((item) => { count += item.quantity; });
    return count;
  }, [cartItems]);

  const handleAddToCart = useCallback((product: Product | Recommendation) => {
    apiClient.trackEvent(customer.customer_id, 'add_to_cart', product.product_id, sessionId);
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
  }, [customer.customer_id, sessionId, showToast]);

  const handleRemoveFromCart = useCallback((productId: string) => {
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
  }, []);

  const currencySymbol = useCallback((currency: string) => currencies[currency] || '$', [currencies]);

  const handleCheckout = useCallback(async () => {
    if (cartItems.size === 0 || submittingOrder) return;
    setSubmittingOrder(true);
    const items = Array.from(cartItems.values()).map(({ product, quantity }) => ({
      product_id: product.product_id,
      quantity,
    }));
    try {
      const order = await apiClient.placeOrder(customer.customer_id, items);
      setCartItems(new Map());
      setShowCart(false);
      showToast(`Order placed! #${order.order_id.slice(0, 8)} — ${formatPrice(order.total_amount, currencySymbol(order.currency))}`);
    } catch (err: any) {
      setShowCart(false);
      const msg = (err?.message || '').replace(/^API error \d+:\s*/, '');
      showToast(msg || 'Checkout failed. Please try again.', 'error');
    } finally {
      setSubmittingOrder(false);
    }
  }, [cartItems, customer.customer_id, submittingOrder, showToast, currencySymbol]);

  const openOrderHistory = useCallback(() => {
    setShowOrders(true);
    setLoadingOrders(true);
    setOrderError(false);
    apiClient.getOrders(customer.customer_id)
      .then((data) => setOrders(data))
      .catch(() => setOrderError(true))
      .finally(() => setLoadingOrders(false));
  }, [customer.customer_id]);

  const handleWishlist = useCallback((product: Product | Recommendation) => {
    apiClient.trackEvent(customer.customer_id, 'wishlist', product.product_id, sessionId);
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
  }, [customer.customer_id, sessionId, showToast]);

  const handleProductClick = useCallback((product: Product | Recommendation) => {
    setSelectedProduct(product);
    apiClient.trackEvent(customer.customer_id, 'page_view', product.product_id, sessionId);
    setRecentlyViewed((prev) => {
      const next = prev.filter((p) => p.product_id !== product.product_id);
      return [product, ...next].slice(0, 10);
    });
  }, [customer.customer_id, sessionId]);

  const closeProductDetail = useCallback(() => {
    setSelectedProduct(null);
  }, []);

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

  const handleConsentToggle = useCallback(async () => {
    const target = !customer.consent_status;
    if (!target && !window.confirm('Withdraw consent for personalisation?\n\nBehavioural tracking will stop and personalised recommendations/offers will be disabled. You can re-enable consent at any time.')) {
      return;
    }
    setUpdatingConsent(true);
    try {
      const updated = await apiClient.updateConsent(customer.customer_id, target);
      setCustomer(updated);
      setRecommendations([]);
      if (!target) {
        showToast('Consent revoked. Personalisation has been turned off.', 'success');
      } else {
        showToast('Consent granted. Personalisation is now enabled.', 'success');
      }
    } catch (err: any) {
      const msg = (err?.message || '').replace(/^API error \d+:\s*/, '');
      showToast(msg || 'Could not update consent. Please try again.', 'error');
    } finally {
      setUpdatingConsent(false);
    }
  }, [customer.customer_id, customer.consent_status, showToast]);

  const handleExportData = useCallback(async () => {
    setExportingData(true);
    try {
      const data = await apiClient.exportCustomerData(customer.customer_id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `personaldata-${customer.customer_id.slice(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast('Your data has been downloaded (right of access).', 'success');
    } catch (err: any) {
      const msg = (err?.message || '').replace(/^API error \d+:\s*/, '');
      showToast(msg || 'Could not download your data. Please try again.', 'error');
    } finally {
      setExportingData(false);
    }
  }, [customer.customer_id, showToast]);

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

  // "Continue Shopping" is cart-based (items added to cart but not purchased).
  // When the customer hasn't added anything yet, fall back to what they viewed
  // so the section shows useful continuation items instead of a misleading
  // cart-empty message.
  const continueProducts = continueShopping.length > 0 ? continueShopping : recentlyViewed;
  const loadingContinueSection = loadingContinue || (continueShopping.length === 0 && loadingRecent);

  return (
    <div className="min-h-screen bg-black">
      <header className="bg-zinc-900/80 border-b border-zinc-800 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
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
                value={navbarSearch}
                onChange={(e) => setNavbarSearch(e.target.value)}
                placeholder="Search products..."
                className="w-full bg-zinc-800/50 text-zinc-100 placeholder-zinc-500 border border-zinc-700/50 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <button onClick={() => setShowCart(true)} className="relative w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <ShoppingCart className="w-4 h-4 text-zinc-300" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 bg-gradient-to-br from-purple-600 to-pink-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center shadow-lg px-1">{cartCount}</span>
              )}
            </button>

            <button onClick={openOrderHistory} title="Order History" className="w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <Receipt className="w-4 h-4 text-zinc-300" />
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

        <div className="max-w-7xl mx-auto px-6 pt-16 pb-16 md:pb-24 text-center">
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
        <section className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {customer.consent_status ? (
                <ShieldCheck className="w-6 h-6 text-emerald-400" />
              ) : (
                <ShieldX className="w-6 h-6 text-red-400" />
              )}
              <div>
                <h3 className="text-sm font-semibold text-zinc-100">Personalisation Consent</h3>
                <p className="text-xs text-zinc-500 mt-0.5">
                  {customer.consent_status
                    ? 'On - recommendations & offers are personalised from your behaviour.'
                    : 'Off - behavioural tracking is stopped and personalisation is disabled.'}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <button
                onClick={() => setShowPrivacy(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-zinc-300 bg-zinc-800/50 hover:bg-zinc-700/50 border border-zinc-700/50 rounded-lg transition-all"
              >
                <Info className="w-3.5 h-3.5" />
                Privacy Policy
              </button>
              <button
                onClick={handleExportData}
                disabled={exportingData}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-zinc-200 bg-zinc-800/50 hover:bg-zinc-700/50 border border-zinc-700/50 rounded-lg transition-all disabled:opacity-50"
                title="Download the data we hold about you (right of access)"
              >
                <Download className="w-3.5 h-3.5" />
                {exportingData ? 'Exporting...' : 'Export My Data'}
              </button>
              <button
                onClick={handleConsentToggle}
                disabled={updatingConsent}
                className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-all disabled:opacity-50 ${
                  customer.consent_status
                    ? 'bg-rose-600/20 text-rose-300 border border-rose-600/40 hover:bg-rose-600/30'
                    : 'bg-emerald-600/20 text-emerald-300 border border-emerald-600/40 hover:bg-emerald-600/30'
                }`}
              >
                {customer.consent_status ? (
                  <><ShieldX className="w-3.5 h-3.5" />{updatingConsent ? 'Updating...' : 'Revoke Consent'}</>
                ) : (
                  <><ShieldCheck className="w-3.5 h-3.5" />{updatingConsent ? 'Updating...' : 'Enable Consent'}</>
                )}
              </button>
            </div>
          </div>
        </section>

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
                <PremiumProductCard key={rec.product_id} product={rec} showAddToCart={false} onAddToCart={handleAddToCart} onWishlist={handleWishlist} onClick={handleProductClick} isWishlisted={wishlistItems.has(rec.product_id)} />
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
                <PremiumProductCard key={product.product_id} product={product} onAddToCart={handleAddToCart} onWishlist={handleWishlist} onClick={handleProductClick} isWishlisted={wishlistItems.has(product.product_id)} />
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

          {loadingContinueSection && <SkeletonGrid count={5} />}

          {!loadingContinueSection && continueProducts.length === 0 && (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
              <p className="text-sm text-zinc-400">Nothing here yet. Start browsing or add items to your cart to see suggestions.</p>
            </div>
          )}

          {!loadingContinueSection && continueProducts.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {continueProducts.map((product) => (
                <PremiumProductCard key={product.product_id} product={product} onAddToCart={handleAddToCart} onWishlist={handleWishlist} onClick={handleProductClick} isWishlisted={wishlistItems.has(product.product_id)} />
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
          <ProductSearch showAllOnMount customerId={customer.customer_id} externalQuery={navbarSearch} onExternalQueryChange={setNavbarSearch} onAddToCart={handleAddToCart} onWishlist={handleWishlist} onProductClick={handleProductClick} />
        </section>
      </main>

      {selectedProduct && (
        <ProductDetailModal
          product={selectedProduct}
          onClose={closeProductDetail}
          onAddToCart={handleAddToCart}
          onWishlist={handleWishlist}
          isWishlisted={wishlistItems.has(selectedProduct.product_id)}
        />
      )}

      {showCart && (
        <CartPanel
          items={cartItems}
          onClose={() => setShowCart(false)}
          onRemove={handleRemoveFromCart}
          onCheckout={handleCheckout}
          submitting={submittingOrder}
        />
      )}

      {showOrders && (
        <OrderHistoryModal
          orders={orders}
          symbolFor={currencySymbol}
          onClose={() => setShowOrders(false)}
          loading={loadingOrders}
          error={orderError}
        />
      )}

      {showPrivacy && (
        <PrivacyModal onClose={() => setShowPrivacy(false)} />
      )}

      <Toast toast={toast} />
    </div>
  );
}
