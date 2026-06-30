import { useState, useEffect, useRef, useCallback } from 'react';
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

function ProductCard({ product }: { product: Product }) {
  const Icon = getCategoryIcon(product.category);
  const colorClass = CATEGORY_COLORS[product.category] || 'from-slate-500/20 to-slate-600/10 border-slate-700/30';
  const iconColor = CATEGORY_ICON_COLORS[product.category] || 'text-slate-400';

  return (
    <div className={`card card-hover overflow-hidden group`}>
      {/* Image / Icon Area */}
      <div className={`h-36 bg-gradient-to-br ${colorClass} flex items-center justify-center relative overflow-hidden`}>
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-300"
            onError={(e) => {
              // Hide broken image, show icon fallback
              (e.target as HTMLImageElement).style.display = 'none';
              (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
            }}
          />
        ) : null}
        <div className={`${product.image_url ? 'hidden' : 'flex'} items-center justify-center`}>
          <Icon className={`w-14 h-14 ${iconColor} opacity-60 group-hover:opacity-90 transition-opacity`} />
        </div>
        {/* Category badge */}
        <span className="absolute top-2 right-2 bg-slate-900/70 backdrop-blur-sm text-[10px] font-medium text-slate-300 px-2 py-0.5 rounded-full border border-slate-700/50">
          {product.category}
        </span>
      </div>

      {/* Info */}
      <div className="p-4">
        <h3 className="text-sm font-semibold text-slate-100 truncate group-hover:text-primary-300 transition-colors" title={product.name}>
          {product.name}
        </h3>
        {product.brand && (
          <p className="text-xs text-slate-500 mt-0.5">{product.brand}</p>
        )}
        {product.subcategory && (
          <p className="text-xs text-slate-600 mt-0.5 capitalize">{product.subcategory}</p>
        )}
        <div className="flex items-center justify-between mt-3">
          <span className="text-lg font-bold text-accent-400">{formatPrice(product.price, product.symbol)}</span>
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
        className="flex items-center gap-2 bg-slate-800 text-slate-300 border border-slate-700 rounded-lg px-3 py-2.5 text-sm hover:border-slate-600 transition-all whitespace-nowrap"
      >
        {value ? (
          <span className="text-slate-100">{value}</span>
        ) : (
          <span className="text-slate-500">{label}</span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 py-1 max-h-60 overflow-y-auto">
          <button
            onClick={() => { onChange(''); setOpen(false); }}
            className={`w-full text-left px-3 py-2 text-sm transition-colors ${
              !value ? 'bg-primary-500/10 text-primary-300' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            All Categories
          </button>
          {options.map((cat) => {
            const Icon = CATEGORY_ICONS[cat] || Package;
            const col = CATEGORY_ICON_COLORS[cat] || 'text-slate-400';
            return (
              <button
                key={cat}
                onClick={() => { onChange(cat); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 transition-colors ${
                  value === cat ? 'bg-primary-500/10 text-primary-300' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
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

export default function ProductSearch({ showAllOnMount, customerId }: { showAllOnMount?: boolean; customerId?: string }) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [results, setResults] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Load categories on mount
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

  // Auto-load all products if showAllOnMount is set
  useEffect(() => {
    if (showAllOnMount) {
      doSearch('', '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced search when query changes
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

  // When category changes, search immediately
  const handleCategoryChange = useCallback((newCat: string) => {
    setCategory(newCat);
    if (query.trim() || newCat) {
      doSearch(query.trim(), newCat);
    }
  }, [query, doSearch]);

  return (
    <div className="space-y-5">
      {/* Search bar + filters */}
      <div className="card p-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search products by name, brand, or category..."
              className="w-full bg-slate-800 text-slate-100 placeholder-slate-500 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
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

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card overflow-hidden">
              <div className="skeleton h-36 rounded-none" />
              <div className="p-4 space-y-2">
                <div className="skeleton h-4 w-3/4" />
                <div className="skeleton h-3 w-1/2" />
                <div className="skeleton h-6 w-1/3 mt-3" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && searched && results.length === 0 && (
        <div className="card p-12 text-center">
          <Package className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-300 mb-1">No products found</h3>
          <p className="text-sm text-slate-500">
            {query.trim()
              ? `No results for "${query}"${category ? ` in ${category}` : ''}. Try a different search term.`
              : 'Select a category to browse products, or type a search query.'}
          </p>
        </div>
      )}

      {/* Results grid */}
      {!loading && results.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">
              {results.length} product{results.length !== 1 ? 's' : ''} found
              {query.trim() && <> for "<span className="text-slate-300">{query}</span>"</>}
              {category && <> in <span className="text-slate-300">{category}</span></>}
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {results.map((product) => (
              <ProductCard key={product.product_id} product={product} />
            ))}
          </div>
        </>
      )}

      {/* Initial state */}
      {!loading && !searched && (
        <div className="card p-16 text-center">
          <Package className="w-20 h-20 text-slate-700 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-400 mb-2">Product Catalogue</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Search by product name, brand, or category above, or select a category from the dropdown to browse.
          </p>
        </div>
      )}
    </div>
  );
}
