interface ReasonCodeBadgeProps {
  reason_code: string;
}

const reasonCodeMap: Record<string, { label: string; className: string }> = {
  purchased_category: {
    label: 'Category Purchase',
    className: 'bg-emerald-900/40 text-emerald-300 border border-emerald-700/40',
  },
  viewed_category: {
    label: 'Category Browse',
    className: 'bg-blue-900/40 text-blue-300 border border-blue-700/40',
  },
  viewed_product: {
    label: 'Recently Viewed',
    className: 'bg-cyan-900/40 text-cyan-300 border border-cyan-700/40',
  },
  cart_recovery: {
    label: 'Cart Recovery',
    className: 'bg-amber-900/40 text-amber-300 border border-amber-700/40',
  },
  trending_in_segment: {
    label: 'Trending',
    className: 'bg-purple-900/40 text-purple-300 border border-purple-700/40',
  },
  top_pick: {
    label: 'Top Pick',
    className: 'bg-indigo-900/40 text-indigo-300 border border-indigo-700/40',
  },
  popular: {
    label: 'Popular',
    className: 'bg-slate-700/40 text-slate-300 border border-slate-600/40',
  },
};

const defaultMapping = {
  label: 'Recommended',
  className: 'bg-slate-700/40 text-slate-300 border border-slate-600/40',
};

export default function ReasonCodeBadge({ reason_code }: ReasonCodeBadgeProps) {
  const mapping = reasonCodeMap[reason_code] || defaultMapping;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${mapping.className}`}>
      {mapping.label}
    </span>
  );
}
