import { useState, useEffect, useMemo } from 'react';
import {
  Smartphone,
  Shirt,
  Sofa,
  BookOpen,
  Dumbbell,
  Sparkles,
  Gamepad2,
  Apple,
  Package,
  AlertTriangle,
  Star,
} from 'lucide-react';
import { apiClient } from '../api/client';
import ReasonCodeBadge from './ReasonCodeBadge';
import { formatPrice } from '../utils/formatPrice';
import type { Recommendation } from '../types';

interface RecommendationsPanelProps {
  customerId: string;
  consentStatus: boolean;
}

const categoryGradients: Record<string, string> = {
  electronics: 'from-blue-600 to-indigo-700',
  clothing: 'from-pink-600 to-rose-700',
  home: 'from-amber-600 to-orange-700',
  books: 'from-emerald-600 to-teal-700',
  sports: 'from-green-600 to-lime-700',
  beauty: 'from-purple-600 to-fuchsia-700',
  food: 'from-red-600 to-rose-700',
  toys: 'from-cyan-600 to-sky-700',
};

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  electronics: Smartphone,
  clothing: Shirt,
  'home & kitchen': Sofa,
  books: BookOpen,
  sports: Dumbbell,
  beauty: Sparkles,
  toys: Gamepad2,
  grocery: Apple,
};

function getCategoryGradient(category: string): string {
  const key = category.toLowerCase();
  return categoryGradients[key] || 'from-zinc-600 to-zinc-700';
}

function getCategoryIcon(category: string): React.ComponentType<{ className?: string }> {
  const key = category.toLowerCase();
  return categoryIcons[key] || Smartphone;
}

function formatCategoryLabel(category: string): string {
  return category
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function hashId(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
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

function ProductImage({ imageUrl, category }: { imageUrl?: string | null; category: string }) {
  const [showIcon, setShowIcon] = useState(!imageUrl);
  const Icon = getCategoryIcon(category);

  if (showIcon) {
    return <Icon className="w-10 h-10 text-white/70" />;
  }

  return (
    <img
      src={imageUrl!}
      alt=""
      className="w-full h-full object-cover opacity-70"
      loading="lazy"
      onError={() => setShowIcon(true)}
    />
  );
}

export default function RecommendationsPanel({
  customerId,
  consentStatus,
}: RecommendationsPanelProps) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enhancements = useMemo(() => {
    const map: Record<string, { rating: number; discount: number; originalPrice: number }> = {};
    for (const rec of recommendations) {
      const h = hashId(rec.product_id);
      const rating = rec.rating ?? (3.5 + (h % 15) / 10);
      const hasDiscount = (h % 5) !== 0;
      const discount = rec.discount_percent ?? (hasDiscount ? 10 + (h % 25) : 0);
      const originalPrice = rec.original_price ?? (discount > 0 ? Math.round(rec.price / (1 - discount / 100) * 100) / 100 : rec.price);
      map[rec.product_id] = {
        rating: Math.min(5, Math.round(rating * 10) / 10),
        discount,
        originalPrice,
      };
    }
    return map;
  }, [recommendations]);

  useEffect(() => {
    if (!customerId || !consentStatus) return;
    setLoading(true);
    setError(null);
    apiClient
      .getRecommendations(customerId)
      .then(setRecommendations)
      .catch((err) => {
        setError(err.message || 'Failed to load recommendations');
        setRecommendations([]);
      })
      .finally(() => setLoading(false));
  }, [customerId, consentStatus]);

  if (!consentStatus) {
    return (
      <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
          Personalised Recommendations
        </h3>
        <div className="flex items-start gap-3 bg-amber-900/20 border border-amber-700/30 rounded-xl p-4">
          <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-300">Consent Required</p>
            <p className="text-xs text-zinc-400 mt-1">
              This customer has not granted consent for personalisation. Enable consent to view recommendations.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
        Personalised Recommendations
      </h3>

      {loading && (
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-zinc-800/50 rounded-xl overflow-hidden">
              <div className="skeleton h-32 w-full" />
              <div className="p-3 space-y-2">
                <div className="skeleton h-4 w-3/4" />
                <div className="skeleton h-3 w-1/2" />
                <div className="skeleton h-3 w-1/3" />
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="text-center py-8">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm text-zinc-400">Failed to load recommendations</p>
          <p className="text-xs text-zinc-500 mt-1">{error}</p>
        </div>
      )}

      {!loading && !error && recommendations.length === 0 && (
        <div className="text-center py-8">
          <Package className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
          <p className="text-sm text-zinc-500">No recommendations available yet</p>
          <p className="text-xs text-zinc-600 mt-1">Train the model first</p>
        </div>
      )}

      {!loading && !error && recommendations.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {recommendations.map((rec) => {
            const { rating, discount, originalPrice } = enhancements[rec.product_id] || { rating: 0, discount: 0, originalPrice: rec.price };
            return (
              <div
                key={rec.product_id}
                className="bg-zinc-800/50 rounded-xl overflow-hidden border border-zinc-700/30 hover:border-zinc-600/50 transition-all cursor-default"
              >
                <div
                  className={`h-28 bg-gradient-to-br ${getCategoryGradient(rec.category)} flex items-center justify-center relative overflow-hidden`}
                >
                  <span className="absolute top-2 left-2 bg-black/30 backdrop-blur-sm text-[10px] font-medium text-white/90 px-2 py-0.5 rounded-full">
                    {formatCategoryLabel(rec.category)}
                  </span>
                  {discount > 0 && (
                    <span className="absolute top-2 right-2 bg-gradient-to-r from-rose-600 to-pink-600 text-white text-[9px] font-bold px-2 py-0.5 rounded-full shadow-lg">
                      {discount}% OFF
                    </span>
                  )}
                  <ProductImage imageUrl={rec.image_url} category={rec.category} />
                </div>
                <div className="p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-medium text-zinc-200 leading-tight line-clamp-2">
                      {rec.name}
                    </h4>
                    <ReasonCodeBadge reason_code={rec.reason_code} />
                  </div>
                  <p className="text-xs text-zinc-400 italic line-clamp-2">{rec.reason_text}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-zinc-400">{rec.brand}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-bold text-purple-400">
                        {formatPrice(rec.price, rec.symbol)}
                      </span>
                      {originalPrice > rec.price && (
                        <span className="text-[10px] text-zinc-600 line-through">
                          {formatPrice(originalPrice, rec.symbol)}
                        </span>
                      )}
                    </div>
                  </div>
                  <StarRating rating={rating} />
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-zinc-500">Score</span>
                    <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full transition-all"
                        style={{ width: `${Math.round(rec.score * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-zinc-400 font-medium">
                      {Math.round(rec.score * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
