import { useState, useMemo } from 'react';
import {
  Sparkles, ShoppingBag, Search, ShoppingCart, User, Star,
  Package, Smartphone, Shirt, Sofa, BookOpen, Dumbbell,
  Gamepad2, Apple, Heart, Plus, ArrowLeft, RefreshCw, Clock,
  LogOut,
} from 'lucide-react';
import { formatPrice } from '../utils/formatPrice';

const CATEGORY_ICONS: Record<string, typeof Smartphone> = {
  Electronics: Smartphone, Clothing: Shirt, 'Home & Kitchen': Sofa,
  Books: BookOpen, Sports: Dumbbell, Toys: Gamepad2, Grocery: Apple, Beauty: Sparkles,
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
  Electronics: 'text-cyan-400', Clothing: 'text-pink-400',
  'Home & Kitchen': 'text-amber-400', Books: 'text-emerald-400',
  Sports: 'text-blue-400', Beauty: 'text-purple-400',
  Toys: 'text-orange-400', Grocery: 'text-lime-400',
};

interface DemoProduct {
  id: string; name: string; category: string; brand: string;
  price: number; image: string; rating: number; discount: number;
}

const MOCK_PRODUCTS: DemoProduct[] = [
  { id: 'd1', name: 'SonicWire Pro Headphones', category: 'Electronics', brand: 'SoundPro', price: 79.99, image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=300&fit=crop', rating: 4.5, discount: 20 },
  { id: 'd2', name: 'Urban Flex Jacket', category: 'Clothing', brand: 'UrbanWear', price: 129.99, image: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400&h=300&fit=crop', rating: 4.2, discount: 15 },
  { id: 'd3', name: 'Smart Home Hub', category: 'Home & Kitchen', brand: 'HomeAI', price: 149.99, image: 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=300&fit=crop', rating: 4.7, discount: 10 },
  { id: 'd4', name: 'Quantum Reader E-Book', category: 'Books', brand: 'VersePress', price: 14.99, image: 'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&h=300&fit=crop', rating: 4.0, discount: 0 },
  { id: 'd5', name: 'AeroStride Running Shoes', category: 'Sports', brand: 'AeroFit', price: 89.99, image: 'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=400&h=300&fit=crop', rating: 4.3, discount: 25 },
  { id: 'd6', name: 'GlowSkin Serum', category: 'Beauty', brand: 'GlowLab', price: 34.99, image: 'https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=400&h=300&fit=crop', rating: 4.6, discount: 0 },
  { id: 'd7', name: 'BuildMaster Blocks 500pc', category: 'Toys', brand: 'BuildMaster', price: 39.99, image: 'https://images.unsplash.com/photo-1596464716127-f2a82984de30?w=400&h=300&fit=crop', rating: 4.8, discount: 5 },
  { id: 'd8', name: 'FreshHarvest Organic Snacks', category: 'Grocery', brand: 'FreshHarvest', price: 24.99, image: 'https://images.unsplash.com/photo-1488459716781-31db52582fe9?w=400&h=300&fit=crop', rating: 4.1, discount: 0 },
  { id: 'd9', name: 'PixelView 4K Monitor', category: 'Electronics', brand: 'PixelView', price: 349.99, image: 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=400&h=300&fit=crop', rating: 4.4, discount: 12 },
  { id: 'd10', name: 'Cashmere Blend Scarf', category: 'Clothing', brand: 'LuxeWear', price: 59.99, image: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=400&h=300&fit=crop', rating: 4.0, discount: 0 },
];

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

function DemoProductCard({ product, index }: { product: DemoProduct; index: number }) {
  const Icon = getCategoryIcon(product.category);
  const colorClass = CATEGORY_COLORS[product.category] || 'from-zinc-500/20 to-zinc-600/10 border-zinc-700/30';
  const iconColor = CATEGORY_ICON_COLORS[product.category] || 'text-zinc-400';
  const originalPrice = product.discount > 0 ? Math.round(product.price / (1 - product.discount / 100) * 100) / 100 : product.price;

  return (
    <div
      className="group bg-zinc-900/50 border border-zinc-800/50 rounded-2xl overflow-hidden hover:border-zinc-700/50 transition-all duration-300 hover:shadow-xl hover:shadow-purple-600/5 hover:-translate-y-0.5"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className={`relative aspect-[4/3] bg-gradient-to-br ${colorClass} overflow-hidden`}>
        {product.image ? (
          <img
            src={product.image}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
              (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
            }}
          />
        ) : null}
        <div className={`${product.image ? 'hidden' : 'flex'} absolute inset-0 items-center justify-center`}>
          <Icon className={`w-14 h-14 ${iconColor} opacity-50`} />
        </div>
        <span className="absolute top-3 left-3 bg-zinc-900/80 backdrop-blur-sm text-[10px] font-medium text-zinc-300 px-2.5 py-1 rounded-full border border-zinc-700/50">
          {product.category}
        </span>
        {product.discount > 0 && (
          <span className="absolute top-3 right-3 bg-gradient-to-r from-rose-600 to-pink-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-full shadow-lg shadow-rose-600/30">
            {product.discount}% OFF
          </span>
        )}
        <button className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-8 h-8 rounded-full bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center hover:bg-rose-500/80" style={{ right: product.discount > 0 ? undefined : '12px', top: product.discount > 0 ? '48px' : '12px' }}>
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
        <StarRating rating={product.rating} />
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-purple-400">{formatPrice(product.price)}</span>
            {originalPrice > product.price && <span className="text-xs text-zinc-600 line-through">{formatPrice(originalPrice)}</span>}
          </div>
          <button className="w-9 h-9 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 flex items-center justify-center transition-all group/add">
            <ShoppingCart className="w-4 h-4 text-purple-400 group-hover/add:text-purple-300 transition-colors" />
          </button>
        </div>
      </div>
    </div>
  );
}

interface DemoViewProps {
  onBack: () => void;
}

export default function DemoView({ onBack }: DemoViewProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return MOCK_PRODUCTS;
    const q = searchQuery.toLowerCase();
    return MOCK_PRODUCTS.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q) ||
      p.brand.toLowerCase().includes(q)
    );
  }, [searchQuery]);

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
            <span className="text-lg font-bold text-purple-400">PersonalShop</span>
          </div>

          <div className="hidden md:flex flex-1 max-w-md mx-6">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search demo products..."
                className="w-full bg-zinc-800/50 text-zinc-100 placeholder-zinc-500 border border-zinc-700/50 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 bg-zinc-800/50 border border-zinc-700/50 rounded-xl px-2.5 py-1.5">
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
            Browse our demo catalog and see recommendations adapt in real-time.
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
              {searchQuery.trim() ? `Results for "${searchQuery}"` : 'Recommended for You'}
            </h2>
            <button
              onClick={() => setSearchQuery('')}
              className="ml-1 p-1.5 rounded-lg text-zinc-500 hover:text-purple-400 hover:bg-zinc-800/50 transition-all"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {filtered.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {filtered.map((product, i) => (
                <DemoProductCard key={product.id} product={product} index={i} />
              ))}
            </div>
          ) : (
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
              <p className="text-sm text-zinc-400">No matching products found. Try a different search term.</p>
            </div>
          )}
        </section>
      </main>
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
