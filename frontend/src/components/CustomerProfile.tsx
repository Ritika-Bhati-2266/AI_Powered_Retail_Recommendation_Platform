import {
  Eye,
  ShoppingCart,
  Mail,
  Clock,
  Calendar,
  DollarSign,
  Tag,
  TrendingUp,
  User,
  ShieldCheck,
  ShieldX,
} from 'lucide-react';
import { formatPrice } from '../utils/formatPrice';
import { formatSegmentLabel } from '../utils/formatSegmentLabel';
import type { CustomerFull } from '../types';

interface CustomerProfileProps {
  customer: CustomerFull;
}

const segmentColors: Record<string, string> = {
  high_value: 'bg-amber-900/40 text-amber-300 border border-amber-700/40',
  bargain_hunter: 'bg-purple-900/40 text-purple-300 border border-purple-700/40',
  new_user: 'bg-blue-900/40 text-blue-300 border border-blue-700/40',
  lapsed: 'bg-zinc-700/40 text-zinc-300 border border-zinc-600/40',
  cart_abandoner: 'bg-orange-900/40 text-orange-300 border border-orange-700/40',
  brand_loyalist: 'bg-violet-900/40 text-violet-300 border border-violet-700/40',
  window_shopper: 'bg-cyan-900/40 text-cyan-300 border border-cyan-700/40',
  power_user: 'bg-red-900/40 text-red-300 border border-red-700/40',
};

function getSegmentColor(segment: string): string {
  const key = segment.toLowerCase().replace(/\s+/g, '_');
  return segmentColors[key] || 'bg-indigo-900/40 text-indigo-300 border border-indigo-700/40';
}

export default function CustomerProfile({ customer }: CustomerProfileProps) {
  const metrics = [
    {
      label: 'Total Views',
      value: customer.metrics.total_views.toLocaleString(),
      icon: Eye,
      color: 'text-blue-400',
    },
    {
      label: 'Purchases',
      value: customer.metrics.total_purchases.toLocaleString(),
      icon: ShoppingCart,
      color: 'text-emerald-400',
    },
    {
      label: 'Cart Events',
      value: customer.metrics.total_cart_events.toLocaleString(),
      icon: TrendingUp,
      color: 'text-amber-400',
    },
    {
      label: 'Email Engagement',
      value: customer.metrics.total_email_engagement.toLocaleString(),
      icon: Mail,
      color: 'text-purple-400',
    },
    {
      label: 'Avg Session',
      value: `${customer.metrics.avg_session_duration_minutes.toFixed(1)}m`,
      icon: Clock,
      color: 'text-cyan-400',
    },
    {
      label: 'Days Inactive',
      value: customer.metrics.days_since_last_activity.toString(),
      icon: Calendar,
      color: customer.metrics.days_since_last_activity > 30 ? 'text-red-400' : 'text-green-400',
    },
    {
      label: 'Lifetime Value',
      value: formatPrice(customer.metrics.lifetime_value, '$'),
      icon: DollarSign,
      color: 'text-amber-400',
    },
    {
      label: 'Preferred Category',
      value: customer.metrics.preferred_category,
      icon: Tag,
      color: 'text-indigo-400',
    },
    {
      label: 'Price Tier',
      value: customer.metrics.preferred_price_tier,
      icon: Tag,
      color: 'text-pink-400',
    },
  ];

  return (
    <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-5 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
            <User className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-zinc-100">{customer.name}</h2>
            <p className="text-sm text-zinc-400">{customer.email}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {customer.consent_status ? (
            <>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-medium text-emerald-400">Consent Granted</span>
            </>
          ) : (
            <>
              <ShieldX className="w-4 h-4 text-red-400" />
              <span className="text-xs font-medium text-red-400">No Consent</span>
            </>
          )}
        </div>
      </div>

      {customer.segments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {customer.segments.map((seg, idx) => (
            <span
              key={idx}
              className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${getSegmentColor(seg.segment)}`}
            >
              {formatSegmentLabel(seg.segment)}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.label}
              className="bg-zinc-800/50 rounded-xl p-3 border border-zinc-800/30"
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className={`w-3.5 h-3.5 ${metric.color}`} />
                <span className="metric-label">{metric.label}</span>
              </div>
              <span className="metric-value text-sm">{metric.value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
