import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Search,
  Package,
  Smartphone,
  Shirt,
  Sofa,
  BookOpen,
  Dumbbell,
  Sparkles,
  Gamepad2,
  Apple,
  ChevronDown,
  Loader2,
  Star,
  ShoppingCart,
  Heart,
  Plus,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { formatPrice } from '../utils/formatPrice';
import type { Product } from '../types';

const CATEGORY_ICONS: Record<string, typeof Smartphone> = {
  Electronics: Smartphone,
  Clothing: Shirt,
  'Home & Kitchen': Sofa,
  Books: BookOpen,
  Sports: Dumbbell,
  Beauty: Sparkles,
  Toys: Gamepad2,
  Grocery: Apple,
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

function useProductEnhancements(product: Product) {
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

function ProductCard({ product, customerId, onAddToCart, onWishlist }: { product: Product; customerId?: string; onAddToCart?: (product: Product) => void; onWishlist?: (product: Product) => void }) {
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

        <button
          onClick={() => onWishlist?.(product)}
          className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-8 h-8 rounded-full bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center hover:bg-rose-500/80" style={{ right: discount > 0 ? undefined : '12px', top: discount > 0 ? '48px' : '12px' }}>
          <Heart className="w-4 h-4 text-zinc-300" />
        </button>

        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 translate-y-2 group-hover:translate-y-0">
          <button
            onClick={() => onAddToCart?.(product)}
            className="w-full flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur-md text-white text-xs font-semibold py-2.5 rounded-xl border border-white/20 transition-all">
            <Plus className="w-3.5 h-3.5" />
            Add to Cart
          </button>
        </div>
      </div>

      <div className="p-4 space-y-2.5">
        <h3 className="text-sm font-semibold text-zinc-100 truncate group-hover:text-purple-300 transition-colors" title={product.name}>
          {product.name}
        </h3>
        <p className="text-xs text-zinc-500">{product.brand}</p>
        {product.subcategory && (
          <p className="text-xs text-zinc-600">{product.subcategory}</p>
        )}
        <StarRating rating={rating} />
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-purple-400">{formatPrice(product.price, product.symbol)}</span>
            {originalPrice > product.price && (
              <span className="text-xs text-zinc-600 line-through">{formatPrice(originalPrice, product.symbol)}</span>
            )}
          </div>
          <button
            onClick={() => onAddToCart?.(product)}
            className="w-9 h-9 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 flex items-center justify-center transition-all group/add">
            <ShoppingCart className="w-4 h-4 text-purple-400 group-hover/add:text-purple-300 transition-colors" />
          </button>
        </div>
      </div>
    </div>
  );
}

function FilterDropdown({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 bg-zinc-900 text-zinc-300 border border-zinc-800 rounded-xl px-3 py-2.5 text-sm hover:border-zinc-700 transition-all whitespace-nowrap"
      >
        {value ? (
          <span className="text-zinc-100">{value}</span>
        ) : (
          <span className="text-zinc-500">{label}</span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 text-zinc-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-zinc-900 border border-zinc-800 rounded-xl shadow-xl z-50 py-1 max-h-60 overflow-y-auto">
          <button
            onClick={() => { onChange(''); setOpen(false); }}
            className={`w-full text-left px-3 py-2 text-sm transition-colors ${
              !value ? 'bg-purple-500/10 text-purple-300' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            All Categories
          </button>
          {options.map((cat) => {
            const Icon = CATEGORY_ICONS[cat] || Package;
            const col = CATEGORY_ICON_COLORS[cat] || 'text-zinc-400';
            return (
              <button
                key={cat}
                onClick={() => { onChange(cat); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 transition-colors ${
                  value === cat ? 'bg-purple-500/10 text-purple-300' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${col}`} />
                {cat}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function ProductSearch({ showAllOnMount, customerId, externalQuery, onExternalQueryChange, onAddToCart, onWishlist }: {
  showAllOnMount?: boolean;
  customerId?: string;
  externalQuery?: string;
  onExternalQueryChange?: (q: string) => void;
  onAddToCart?: (product: Product) => void;
  onWishlist?: (product: Product) => void;
}) {
  const [query, setQuery] = useState(externalQuery ?? '');
  const [category, setCategory] = useState('');
  const [results, setResults] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    apiClient.getProductCategories().then(setCategories).catch(() => {});
  }, []);

  const doSearch = useCallback(async (q: string, cat: string) => {
    setLoading(true);
    setSearched(true);
    try {
      const data = await apiClient.searchProducts(q, cat || undefined, customerId);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  const prevExternalRef = useRef(externalQuery);

  useEffect(() => {
    if (externalQuery !== undefined && externalQuery !== prevExternalRef.current) {
      prevExternalRef.current = externalQuery;
      setQuery(externalQuery);
    }
  }, [externalQuery]);

  useEffect(() => {
    if (showAllOnMount) {
      doSearch('', '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!query.trim() && !category) {
      setResults([]);
      setSearched(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      doSearch(query.trim(), category);
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [query, category, doSearch]);

  const handleCategoryChange = useCallback((newCat: string) => {
    setCategory(newCat);
    if (query.trim() || newCat) {
      doSearch(query.trim(), newCat);
    }
  }, [query, doSearch]);

  return (
    <div className="space-y-5">
      <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => {
                const value = e.target.value;
                setQuery(value);
                onExternalQueryChange?.(value);
              }}
              placeholder="Search products by name, brand, or category..."
              className="w-full bg-zinc-900 text-zinc-100 placeholder-zinc-500 border border-zinc-800 rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            />
          </div>
          <FilterDropdown
            label="All Categories"
            options={categories}
            value={category}
            onChange={handleCategoryChange}
          />
        </div>
      </div>

      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
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
      )}

      {!loading && searched && results.length === 0 && (
        <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-12 text-center">
          <Package className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-zinc-300 mb-1">No products found</h3>
          <p className="text-sm text-zinc-500">
            {query.trim()
              ? `No results for "${query}"${category ? ` in ${category}` : ''}. Try a different search term.`
              : 'Select a category to browse products, or type a search query.'}
          </p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-xs text-zinc-500">
              {results.length} product{results.length !== 1 ? 's' : ''} found
              {query.trim() && <> for "<span className="text-zinc-300">{query}</span>"</>}
              {category && <> in <span className="text-zinc-300">{category}</span></>}
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {results.map((product) => (
              <ProductCard key={product.product_id} product={product} customerId={customerId} onAddToCart={onAddToCart} onWishlist={onWishlist} />
            ))}
          </div>
        </>
      )}

      {!loading && !searched && (
        <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-16 text-center">
          <Package className="w-20 h-20 text-zinc-700 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-zinc-400 mb-2">Product Catalogue</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            Search by product name, brand, or category above, or select a category from the dropdown to browse.
          </p>
        </div>
      )}
    </div>
  );
}
